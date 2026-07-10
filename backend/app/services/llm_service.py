"""
MedAI Assistant - LLM Service
Enhanced LLM interaction layer that wraps the existing OpenAI/OpenRouter API.
Adds structured output prompting for evidence-based medical responses.
"""
import json
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services.context_builder import ContextResult

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class LLMResponse:
    """Structured response from the LLM."""
    content: str  # Full response text
    confidence: float = 0.5
    sources_used: int = 0
    web_sources_used: int = 0
    search_performed: bool = False
    references: list = field(default_factory=list)
    evidence_summary: str = ""


# Enhanced system prompt addendum for web-search-augmented responses
WEB_SEARCH_PROMPT_ADDENDUM = """
IMPORTANT — EVIDENCE-BASED PHARMACOLOGY RESPONSE INSTRUCTIONS:

You are PharmaGPT, a clinical pharmacology expert. You have been provided with RAG and REAL-TIME SEARCH CONTEXT from trusted medical databases.

When generating your response, you MUST follow this format exactly:

### Mechanism:
Explain the basic pharmacological mechanism of the drug and the interaction.

### Transporters/Enzymes Involved:
Identify all enzymes (CYP450s) and transporters (e.g., OCT1, OCT2, MATE1, MATE2-K, OATP1B1, P-gp) involved. For each transporter, state:
- Its membrane localization (e.g., basolateral/apical, hepatic/renal proximal tubule).
- Its physiological function.
- If the drug is NOT metabolized by CYP450, explicitly state: "This interaction is transporter-mediated rather than CYP-mediated."

### Effect of the Interacting Drug:
Explain how the interacting drug alters the activity or expression of each transporter or enzyme (e.g., inhibition, induction, competition).

### Pharmacokinetic Consequence:
Describe the resulting changes in absorption, distribution, metabolism, or elimination (e.g., Cmax, AUC, clearance, cellular accumulation).

### Clinical Significance:
Explain the therapeutic consequence (e.g., efficacy changes, toxicity risks).

### Key Point:
Provide one concise concluding sentence.

CRITICAL GROUNDING RULES:
- Use ONLY the retrieved evidence to derive pharmacokinetic and clinical consequences.
- Do NOT infer increased clearance, reduced efficacy, increased toxicity, or enhanced effect unless the retrieved evidence explicitly supports the conclusion.
- If evidence is uncertain or conflicting, explicitly state:
  "The effect is variable and its clinical significance is uncertain."
- If a drug is not metabolized by CYP450 enzymes, explicitly state this.
- Do not omit clinically relevant transporters mentioned in the retrieved evidence.
- Do NOT include conversational filler, greetings, or generic safety disclaimers.

FINAL VERIFICATION INSTRUCTION:
Before producing the final answer, verify every clinical conclusion against the retrieved evidence.
For each conclusion ask internally:
- Is this explicitly supported by the retrieved context?
If NO:
- Remove the statement.
- Replace it with:
  "Current evidence does not clearly support this conclusion."

Never infer:
- reduced efficacy
- increased clearance
- increased toxicity
- enhanced effect
unless explicitly stated in the retrieved evidence.
"""

NO_EVIDENCE_RESPONSE = (
    "Current evidence from trusted medical sources is insufficient to answer this question. "
    "I recommend consulting a qualified healthcare professional or searching specialized "
    "medical databases like PubMed for the most current information.\n\n"
    "⚠️ *Disclaimer: I am an AI assistant and cannot provide medical diagnoses.*"
)


class LLMService:
    """
    Enhanced LLM interaction service.

    Wraps the existing OpenAI/OpenRouter API call with structured prompting
    for evidence-based medical responses. Does NOT replace the existing
    _call_openai method — it reuses it.
    """

    async def generate_response(
        self,
        base_system_prompt: str,
        user_message: str,
        context: ContextResult,
    ) -> LLMResponse:
        """
        Generate a structured LLM response using combined context.

        Args:
            base_system_prompt: The original system prompt (with RAG context placeholder already filled).
            user_message: The user's question.
            context: Combined context from context_builder.

        Returns:
            LLMResponse with structured content and metadata.
        """
        # Build enhanced system prompt
        enhanced_prompt = self._build_enhanced_system_prompt(
            base_system_prompt, context
        )

        # Call the existing OpenAI API
        response_text = await self._call_openai(enhanced_prompt, user_message)

        # Build structured response
        llm_response = LLMResponse(
            content=response_text,
            sources_used=context.rag_sources_count,
            web_sources_used=context.web_sources_count,
            search_performed=context.source_type != "rag_only",
            references=context.references,
            evidence_summary=context.evidence_summary,
        )

        # Calculate confidence based on available evidence
        llm_response.confidence = self._calculate_enhanced_confidence(context)

        return llm_response

    def _build_enhanced_system_prompt(
        self, base_prompt: str, context: ContextResult
    ) -> str:
        """
        Enhance the base system prompt with web search context and instructions.
        """
        # Replace the RAG context placeholder in the base prompt with combined context
        enhanced = base_prompt.replace(
            "No specific medical context retrieved for this query.",
            context.combined_context,
        )

        # If we have any RAG context already in the prompt, append web context
        if context.web_context and context.combined_context not in enhanced:
            # The base prompt already has RAG context formatted; append web results
            enhanced += f"\n\n{context.web_context}"

        # Add web search instructions if web results are present
        if context.source_type != "rag_only":
            enhanced += f"\n\n{WEB_SEARCH_PROMPT_ADDENDUM}"

            # Add reference list for the LLM to cite
            if context.references:
                ref_list = "\n".join(
                    f"[Source {i+1}]: {ref['title']} ({ref['source']}) - {ref['url']}"
                    for i, ref in enumerate(context.references)
                )
                enhanced += f"\n\nAVAILABLE REFERENCES:\n{ref_list}"

        return enhanced

    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """
        Call OpenAI/OpenRouter API for chat completion.
        This mirrors the existing implementation in ai_chat.py.
        """
        if not settings.OPENAI_API_KEY:
            return self._generate_fallback_response(user_message)

        try:
            from openai import OpenAI

            extra_headers = {}
            if settings.OPENAI_API_BASE and "openrouter.ai" in settings.OPENAI_API_BASE:
                extra_headers = {
                    "HTTP-Referer": "https://github.com/Vedansh/Diabetes-Chatbot",
                    "X-Title": "MedAI Assistant",
                }

            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE if settings.OPENAI_API_BASE else None,
                default_headers=extra_headers if extra_headers else None,
            )

            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=2500,  # Increased for structured responses with citations
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

    def _calculate_enhanced_confidence(self, context: ContextResult) -> float:
        """
        Calculate confidence score based on available evidence quality.

        Factors:
        - Number of RAG sources
        - Number of web sources
        - Source credibility scores
        - Whether both RAG and web agree
        """
        base_confidence = 0.3  # Minimum confidence

        # RAG contribution
        if context.rag_sources_count > 0:
            base_confidence += min(0.25, context.rag_sources_count * 0.05)

        # Web search contribution
        if context.web_sources_count > 0:
            # Average credibility of web sources
            if context.references:
                avg_credibility = sum(
                    r.get("credibility_score", 0.5) for r in context.references
                ) / len(context.references)
                base_confidence += avg_credibility * 0.3

        # Bonus for having both RAG and web sources (cross-validation)
        if context.source_type == "rag_and_web":
            base_confidence += 0.1

        return round(min(0.95, base_confidence), 2)


# Singleton instance
llm_service = LLMService()
