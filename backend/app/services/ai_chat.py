"""
MedAI Assistant - AI Chat Service
Conversational AI with LangChain, RAG integration, real-time web search, and emergency detection.
"""
import json
import logging
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.services.emergency import emergency_detector
from app.services.rag_engine import rag_engine
from app.services.search_service import search_service
from app.services.retriever import retriever
from app.services.medical_source_filter import medical_source_filter
from app.services.context_builder import context_builder, ContextResult
from app.services.llm_service import llm_service
from app.services.cache_service import cache_service, CachedSearchResult
from app.models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()

# System prompt for the medical AI assistant
MEDICAL_SYSTEM_PROMPT = """You are MedAI Assistant, a professional and empathetic AI healthcare assistant.

CRITICAL RULES — YOU MUST FOLLOW THESE AT ALL TIMES:
1. NEVER provide a definitive medical diagnosis. Always say "possible" or "potential" conditions.
2. NEVER prescribe specific medication dosages.
3. ALWAYS include a confidence level (Low/Moderate/High) with your assessments.
4. ALWAYS recommend consulting a qualified healthcare professional.
5. ALWAYS include a brief disclaimer that you are an AI assistant.
6. Be empathetic, professional, and clear in your responses.
7. Ask dynamic follow-up questions to better understand the patient's condition.
8. When given medical context from retrieved documents, use it to ground your responses.
9. If the user speaks in Hindi, respond in Hindi. Otherwise respond in English.
10. Present information in a structured, easy-to-understand format.

RESPONSE FORMAT:
- Start with acknowledging the patient's concern
- Ask clarifying follow-up questions if needed
- Provide relevant health information
- List possible conditions (if applicable) with confidence levels
- Suggest next steps
- End with a brief safety disclaimer

MEDICAL CONTEXT (from knowledge base):
{rag_context}

PATIENT PROFILE:
{patient_context}

CONVERSATION HISTORY:
{conversation_history}
"""

HINDI_SYSTEM_ADDENDUM = """
LANGUAGE NOTE: The patient prefers Hindi. Respond primarily in Hindi (Devanagari script),
but include English medical terms in parentheses for clarity.
"""


class AIChatService:
    """Manages AI-powered medical conversations."""

    async def create_session(
        self, db: AsyncSession, user_id: str, title: str = "New Conversation", language: str = "en"
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            language=language,
        )
        db.add(session)
        await db.flush()
        return session

    async def get_sessions(
        self, db: AsyncSession, user_id: str, limit: int = 20
    ) -> List[ChatSession]:
        """Get chat sessions for a user."""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_session_messages(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> List[ChatMessage]:
        """Get all messages in a chat session."""
        result = await db.execute(
            select(ChatMessage)
            .join(ChatSession)
            .where(
                ChatMessage.session_id == session_id,
                ChatSession.user_id == user_id,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()

    async def send_message(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        content: str,
        patient_context: str = "",
    ) -> dict:
        """
        Process a user message and generate an AI response.

        Pipeline:
        1. Emergency detection
        2. RAG context retrieval
        3. Determine if web search is needed
        4. Web search (if needed) with caching
        5. Build unified context
        6. Generate LLM response with structured output

        Returns dict with user_message, ai_message, is_emergency, etc.
        """
        # Verify session belongs to user
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Chat session not found")

        # Save user message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(user_msg)

        # ── Emergency Detection ──────────────────────────────────────────
        emergency = emergency_detector.check_message(content)
        if emergency:
            emergency_response = emergency_detector.get_emergency_response(emergency)
            ai_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=emergency_response,
                is_emergency=True,
                metadata_json=json.dumps({
                    "emergency_category": emergency["category"],
                    "emergency_severity": emergency["severity"],
                    "confidence": 1.0,
                }),
            )
            db.add(ai_msg)
            await db.flush()

            return {
                "user_message": user_msg,
                "ai_message": ai_msg,
                "is_emergency": True,
                "emergency_message": emergency["message"],
                "confidence": 1.0,
                "sources_used": 0,
                "web_sources_used": 0,
                "search_performed": False,
                "references": [],
                "evidence_summary": None,
            }

        # ── RAG Context Retrieval ────────────────────────────────────────
        rag_results = await rag_engine.query_hybrid(content, n_results=5)
        sources_used = len(rag_results)

        # ── Web Search Pipeline ──────────────────────────────────────────
        web_results = []
        search_performed = False

        if settings.WEB_SEARCH_ENABLED:
            # Check cache first
            cached = cache_service.get(content)

            if cached:
                web_results_dicts = cached.web_results
                # Reconstruct RetrievedDocument objects from cached dicts
                from app.services.retriever import RetrievedDocument
                web_results = [
                    RetrievedDocument.from_dict(d) if isinstance(d, dict) else d
                    for d in web_results_dicts
                ]
                search_performed = True
                logger.info(f"Using {len(web_results)} cached web results")

            elif context_builder.needs_web_search(content, rag_results):
                # Check session context for follow-up questions
                session_context = cache_service.get_session_context(session_id)
                if session_context:
                    from app.services.retriever import RetrievedDocument
                    web_results = [
                        RetrievedDocument.from_dict(d) if isinstance(d, dict) else d
                        for d in session_context
                    ]
                    search_performed = True
                    logger.info(f"Reusing {len(web_results)} session context results")
                else:
                    # Perform actual web search
                    try:
                        search_results = await search_service.search(content)
                        if search_results:
                            raw_documents = await retriever.retrieve(search_results)
                            web_results = medical_source_filter.filter_and_rank(raw_documents)

                            # Cache the results
                            cache_service.set(
                                content,
                                CachedSearchResult(
                                    web_results=[d.to_dict() for d in web_results]
                                ),
                            )
                            cache_service.set_session_context(
                                session_id,
                                [d.to_dict() for d in web_results],
                            )
                            search_performed = True
                            logger.info(f"Web search returned {len(web_results)} results")
                    except Exception as e:
                        logger.error(f"Web search pipeline failed: {e}")
                        # Continue with RAG-only — graceful degradation

        # ── Build Unified Context ────────────────────────────────────────
        context = context_builder.build_context(rag_results, web_results, content)

        # Format RAG context for the system prompt
        rag_context = ""
        if rag_results:
            context_parts = []
            for i, result in enumerate(rag_results, 1):
                doc = result["document"]
                source = result.get("metadata", {}).get("source", "medical_knowledge")
                context_parts.append(f"[Source {i} ({source})]: {doc}")
            rag_context = "\n\n".join(context_parts)
        else:
            rag_context = "No specific medical context retrieved for this query."

        # ── Conversation History ─────────────────────────────────────────
        history_messages = await self.get_session_messages(db, session_id, user_id)
        conversation_history = ""
        # Use last 10 messages for context
        recent_messages = history_messages[-10:] if len(history_messages) > 10 else history_messages
        for msg in recent_messages:
            role_label = "Patient" if msg.role == "user" else "Assistant"
            conversation_history += f"{role_label}: {msg.content}\n\n"

        # ── Generate AI Response ─────────────────────────────────────────
        system_prompt = MEDICAL_SYSTEM_PROMPT.format(
            rag_context=rag_context,
            patient_context=patient_context or "No patient profile available.",
            conversation_history=conversation_history or "This is the start of the conversation.",
        )

        if session.language == "hi":
            system_prompt += HINDI_SYSTEM_ADDENDUM

        # Use enhanced LLM service with web context
        llm_response = await llm_service.generate_response(
            system_prompt, content, context
        )

        ai_response_text = llm_response.content
        confidence = llm_response.confidence

        # Build metadata with web search information
        metadata = {
            "confidence": confidence,
            "sources_used": sources_used,
            "rag_distances": [r.get("distance", 0) for r in rag_results],
            "web_sources_used": llm_response.web_sources_used,
            "search_performed": llm_response.search_performed,
            "references": llm_response.references,
            "evidence_summary": llm_response.evidence_summary,
        }

        ai_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=ai_response_text,
            is_emergency=False,
            metadata_json=json.dumps(metadata),
        )
        db.add(ai_msg)

        # Update session title if it's the first message
        if len(history_messages) <= 1:
            session.title = content[:100] if len(content) > 100 else content

        await db.flush()

        return {
            "user_message": user_msg,
            "ai_message": ai_msg,
            "is_emergency": False,
            "emergency_message": None,
            "confidence": confidence,
            "sources_used": sources_used,
            "web_sources_used": llm_response.web_sources_used,
            "search_performed": llm_response.search_performed,
            "references": llm_response.references,
            "evidence_summary": llm_response.evidence_summary,
        }

    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """Call OpenAI API for chat completion."""
        if not settings.OPENAI_API_KEY:
            return self._generate_fallback_response(user_message)

        try:
            from openai import OpenAI

            extra_headers = {}
            if settings.OPENAI_API_BASE and "openrouter.ai" in settings.OPENAI_API_BASE:
                extra_headers = {
                    "HTTP-Referer": "https://github.com/Vedansh/Diabetes-Chatbot",
                    "X-Title": "MedAI Assistant"
                }

            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE if settings.OPENAI_API_BASE else None,
                default_headers=extra_headers if extra_headers else None
            )
            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._generate_fallback_response(user_message)

    def _generate_fallback_response(self, user_message: str) -> str:
        """Generate a fallback response when OpenAI is unavailable."""
        return (
            "Thank you for reaching out. I understand you have a health concern.\n\n"
            "I'm currently experiencing a temporary connection issue with my AI engine. "
            "However, I want to ensure your safety:\n\n"
            "• If this is an **emergency**, please call **112** (India) or your local emergency number immediately.\n"
            "• For **non-emergency concerns**, please try again in a few moments.\n"
            "• Always consult a **qualified healthcare professional** for medical advice.\n\n"
            "⚠️ *Disclaimer: I am an AI assistant and cannot provide medical diagnoses.*"
        )

    def _calculate_confidence(self, rag_results: List[dict]) -> float:
        """Calculate response confidence based on RAG retrieval quality."""
        if not rag_results:
            return 0.3  # Low confidence without supporting evidence

        # Average distance (lower = better match in cosine space)
        distances = [r.get("distance", 1.0) for r in rag_results]
        avg_distance = sum(distances) / len(distances)

        # Convert distance to confidence (cosine distance: 0 = identical, 2 = opposite)
        confidence = max(0.1, min(0.95, 1.0 - (avg_distance / 2)))
        return round(confidence, 2)


# Singleton instance
ai_chat_service = AIChatService()
