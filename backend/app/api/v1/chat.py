"""
MedAI Assistant - Chat API
AI-powered medical chat conversations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.patient import PatientProfile, ChronicCondition, Medication, Allergy
from app.services.ai_chat import ai_chat_service
from app.schemas.schemas import (
    ChatSessionCreate, ChatSessionResponse,
    ChatMessageSend, ChatMessageResponse, ChatAIResponse,
    WebReference,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session."""
    session = await ai_chat_service.create_session(
        db, current_user.id, data.title, data.language
    )
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        language=session.language,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's chat sessions."""
    sessions = await ai_chat_service.get_sessions(db, current_user.id)
    result = []
    for s in sessions:
        # Count messages
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        )
        msg_count = count_result.scalar() or 0

        result.append(ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            language=s.language,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=msg_count,
        ))
    return result


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    sessions = result.scalars().all()
    for s in sessions:
        await db.delete(s)
    return None


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    await db.delete(session)
    await db.commit()
    return None


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a chat session."""
    messages = await ai_chat_service.get_session_messages(db, session_id, current_user.id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/sessions/{session_id}/messages", response_model=ChatAIResponse)
async def send_message(
    session_id: str,
    data: ChatMessageSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get AI response."""
    # Build patient context
    patient_context = await _build_patient_context(db, current_user.id)

    result = await ai_chat_service.send_message(
        db, session_id, current_user.id, data.content, patient_context
    )

    return ChatAIResponse(
        user_message=ChatMessageResponse.model_validate(result["user_message"]),
        ai_message=ChatMessageResponse.model_validate(result["ai_message"]),
        is_emergency=result["is_emergency"],
        emergency_message=result.get("emergency_message"),
        confidence=result.get("confidence"),
        sources_used=result.get("sources_used", 0),
        web_sources_used=result.get("web_sources_used", 0),
        search_performed=result.get("search_performed", False),
        references=[
            WebReference(**ref) for ref in result.get("references", [])
        ],
        evidence_summary=result.get("evidence_summary"),
    )


async def _build_patient_context(db: AsyncSession, user_id: str) -> str:
    """Build patient context string for the AI."""
    parts = []

    profile_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    if profile:
        if profile.gender:
            parts.append(f"Gender: {profile.gender}")
        if profile.date_of_birth:
            from datetime import date
            age = (date.today() - profile.date_of_birth).days // 365
            parts.append(f"Age: {age} years")
        if profile.weight_kg and profile.height_cm:
            bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
            parts.append(f"BMI: {bmi:.1f}")

        # Chronic conditions
        chronic_result = await db.execute(
            select(ChronicCondition).where(ChronicCondition.patient_id == profile.id)
        )
        conditions = chronic_result.scalars().all()
        if conditions:
            parts.append(f"Chronic Conditions: {', '.join(c.condition_name for c in conditions)}")

        # Active medications
        med_result = await db.execute(
            select(Medication).where(
                Medication.patient_id == profile.id, Medication.is_active == True
            )
        )
        meds = med_result.scalars().all()
        if meds:
            parts.append(f"Active Medications: {', '.join(m.name for m in meds)}")

        # Allergies
        allergy_result = await db.execute(
            select(Allergy).where(Allergy.patient_id == profile.id)
        )
        allergies = allergy_result.scalars().all()
        if allergies:
            parts.append(f"Allergies: {', '.join(a.allergen for a in allergies)}")

    return "\n".join(parts) if parts else "No patient profile available."
