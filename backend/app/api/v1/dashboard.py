"""
MedAI Assistant - Dashboard API
Aggregated patient dashboard data.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.report import MedicalReport, LabValue
from app.models.patient import PatientProfile, ChronicCondition, Medication, Allergy
from app.services.health_score import health_score_calculator
from app.schemas.schemas import (
    DashboardResponse, HealthScoreResponse,
    ReportResponse, ChatSessionResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated dashboard data for the current patient."""

    # ── Health Score ──
    score_data = await health_score_calculator.calculate(db, current_user.id)
    health_score = HealthScoreResponse(**score_data)

    # ── Recent Reports (last 5) ──
    report_result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.upload_date.desc())
        .limit(5)
    )
    recent_reports = [
        ReportResponse.model_validate(r)
        for r in report_result.scalars().all()
    ]

    # ── Active Conditions ──
    profile_result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    active_conditions = []
    active_medications = 0
    allergies_count = 0

    if profile:
        cond_result = await db.execute(
            select(ChronicCondition).where(ChronicCondition.patient_id == profile.id)
        )
        active_conditions = [c.condition_name for c in cond_result.scalars().all()]

        med_result = await db.execute(
            select(func.count(Medication.id)).where(
                Medication.patient_id == profile.id,
                Medication.is_active == True,
            )
        )
        active_medications = med_result.scalar() or 0

        allergy_result = await db.execute(
            select(func.count(Allergy.id)).where(Allergy.patient_id == profile.id)
        )
        allergies_count = allergy_result.scalar() or 0

    # ── Recent Chat Sessions (last 3) ──
    session_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(3)
    )
    recent_sessions = []
    for s in session_result.scalars().all():
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        )
        msg_count = count_result.scalar() or 0
        recent_sessions.append(ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            language=s.language,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=msg_count,
        ))

    # ── Risk Indicators ──
    risk_indicators = []
    # Check for critical lab values
    critical_result = await db.execute(
        select(func.count(LabValue.id))
        .join(MedicalReport)
        .where(
            MedicalReport.user_id == current_user.id,
            LabValue.is_critical == True,
        )
    )
    critical_count = critical_result.scalar() or 0
    if critical_count > 0:
        risk_indicators.append({
            "type": "critical_labs",
            "level": "high",
            "message": f"{critical_count} critical lab value(s) found",
            "icon": "alert-triangle",
        })

    if len(active_conditions) >= 3:
        risk_indicators.append({
            "type": "chronic_conditions",
            "level": "moderate",
            "message": f"{len(active_conditions)} chronic conditions tracked",
            "icon": "activity",
        })

    # ── Health Insights ──
    health_insights = score_data.get("recommendations", [])

    return DashboardResponse(
        health_score=health_score,
        recent_reports=recent_reports,
        active_conditions=active_conditions,
        active_medications=active_medications,
        allergies_count=allergies_count,
        recent_chat_sessions=recent_sessions,
        risk_indicators=risk_indicators,
        health_insights=health_insights,
    )
