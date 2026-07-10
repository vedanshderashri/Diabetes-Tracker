"""
MedAI Assistant - Doctor Summary API
Clinical summary generation for healthcare providers.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.doctor_summary import doctor_summary_generator
from app.schemas.schemas import DoctorSummaryRequest, DoctorSummaryResponse

router = APIRouter(prefix="/summary", tags=["Doctor Summary"])


@router.post("/generate", response_model=DoctorSummaryResponse)
async def generate_summary(
    data: DoctorSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a doctor-facing clinical summary for the current patient."""
    # Use patient_id from request or default to current user
    target_user_id = data.patient_id or current_user.id

    # Only admins/doctors can view other patients' summaries
    if target_user_id != current_user.id and current_user.role == "patient":
        target_user_id = current_user.id

    result = await doctor_summary_generator.generate_summary(
        db=db,
        user_id=target_user_id,
        include_reports=data.include_reports,
        include_chat_history=data.include_chat_history,
    )

    return DoctorSummaryResponse(**result)
