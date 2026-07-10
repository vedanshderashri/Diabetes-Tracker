"""
MedAI Assistant - Admin API
User management, analytics, system monitoring.
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.report import MedicalReport
from app.services.disease_predictor import disease_predictor
from app.services.rag_engine import rag_engine
from app.schemas.schemas import (
    AdminUserListResponse, UserResponse,
    SystemHealthResponse, AnalyticsResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

_start_time = time.time()


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all users (admin only)."""
    offset = (page - 1) * per_page

    # Get total count
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar() or 0

    # Get paginated users
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = [UserResponse.model_validate(u) for u in result.scalars().all()]

    return AdminUserListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get system analytics (admin only)."""
    # Total counts
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    reports_count = (await db.execute(select(func.count(MedicalReport.id)))).scalar() or 0
    sessions_count = (await db.execute(select(func.count(ChatSession.id)))).scalar() or 0
    messages_count = (await db.execute(select(func.count(ChatMessage.id)))).scalar() or 0

    # Reports by type
    report_types = await db.execute(
        select(MedicalReport.report_type, func.count(MedicalReport.id))
        .group_by(MedicalReport.report_type)
    )
    reports_by_type = {
        (rtype or "unknown"): count for rtype, count in report_types.all()
    }

    # Users by role
    user_roles = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    users_by_role = {role: count for role, count in user_roles.all()}

    return AnalyticsResponse(
        total_users=users_count,
        total_reports=reports_count,
        total_chat_sessions=sessions_count,
        total_messages=messages_count,
        reports_by_type=reports_by_type,
        users_by_role=users_by_role,
        daily_activity=[],
    )


@router.get("/system", response_model=SystemHealthResponse)
async def system_health(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get system health status (admin only)."""
    # DB check
    try:
        await db.execute(select(func.count(User.id)))
        db_status = "healthy"
    except Exception:
        db_status = "error"

    # Vector store check
    vector_stats = rag_engine.get_collection_stats()

    # ML models check
    ml_status = disease_predictor.get_model_status()

    # Counts
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    reports_count = (await db.execute(select(func.count(MedicalReport.id)))).scalar() or 0
    sessions_count = (await db.execute(select(func.count(ChatSession.id)))).scalar() or 0

    return SystemHealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        vector_store=vector_stats.get("status", "unknown"),
        ml_models=ml_status,
        uptime_seconds=time.time() - _start_time,
        total_users=users_count,
        total_reports=reports_count,
        total_chat_sessions=sessions_count,
    )
