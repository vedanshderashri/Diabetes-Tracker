"""
MedAI Assistant - Patient API
Patient profile, medical history, medications, and allergies management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.patient import (
    PatientProfile, MedicalHistory, Medication, Allergy, ChronicCondition,
)
from app.schemas.schemas import (
    PatientProfileCreate, PatientProfileResponse,
    MedicalHistoryCreate, MedicalHistoryResponse,
    MedicationCreate, MedicationResponse,
    AllergyCreate, AllergyResponse,
    ChronicConditionCreate, ChronicConditionResponse,
)

router = APIRouter(prefix="/patients", tags=["Patient Profile"])


# ── Profile ──────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=PatientProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's patient profile."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return PatientProfileResponse.model_validate(profile)


@router.put("/profile", response_model=PatientProfileResponse)
async def update_profile(
    data: PatientProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update patient profile."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = PatientProfile(id=str(uuid.uuid4()), user_id=current_user.id)
        db.add(profile)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.flush()
    return PatientProfileResponse.model_validate(profile)


# ── Medical History ──────────────────────────────────────────────────────────

@router.get("/medical-history", response_model=list[MedicalHistoryResponse])
async def list_medical_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(MedicalHistory).where(MedicalHistory.patient_id == profile.id)
    )
    return [MedicalHistoryResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/medical-history", response_model=MedicalHistoryResponse, status_code=201)
async def add_medical_history(
    data: MedicalHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    history = MedicalHistory(
        id=str(uuid.uuid4()),
        patient_id=profile.id,
        **data.model_dump(),
    )
    db.add(history)
    await db.flush()
    return MedicalHistoryResponse.model_validate(history)


# ── Medications ──────────────────────────────────────────────────────────────

@router.get("/medications", response_model=list[MedicationResponse])
async def list_medications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(Medication).where(Medication.patient_id == profile.id)
    )
    return [MedicationResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/medications", response_model=MedicationResponse, status_code=201)
async def add_medication(
    data: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    medication = Medication(
        id=str(uuid.uuid4()),
        patient_id=profile.id,
        **data.model_dump(),
    )
    db.add(medication)
    await db.flush()
    return MedicationResponse.model_validate(medication)


# ── Allergies ────────────────────────────────────────────────────────────────

@router.get("/allergies", response_model=list[AllergyResponse])
async def list_allergies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(Allergy).where(Allergy.patient_id == profile.id)
    )
    return [AllergyResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(
    data: AllergyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    allergy = Allergy(
        id=str(uuid.uuid4()),
        patient_id=profile.id,
        **data.model_dump(),
    )
    db.add(allergy)
    await db.flush()
    return AllergyResponse.model_validate(allergy)


# ── Chronic Conditions ───────────────────────────────────────────────────────

@router.get("/chronic-conditions", response_model=list[ChronicConditionResponse])
async def list_chronic_conditions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(ChronicCondition).where(ChronicCondition.patient_id == profile.id)
    )
    return [ChronicConditionResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/chronic-conditions", response_model=ChronicConditionResponse, status_code=201)
async def add_chronic_condition(
    data: ChronicConditionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    condition = ChronicCondition(
        id=str(uuid.uuid4()),
        patient_id=profile.id,
        **data.model_dump(),
    )
    db.add(condition)
    await db.flush()
    return ChronicConditionResponse.model_validate(condition)


# ── Delete Endpoints ──────────────────────────────────────────────────────────

@router.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a medication."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    med_result = await db.execute(
        select(Medication).where(
            Medication.id == medication_id,
            Medication.patient_id == profile.id
        )
    )
    medication = med_result.scalar_one_or_none()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    await db.delete(medication)
    return None


@router.delete("/medical-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_history(
    history_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a medical history record."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    hist_result = await db.execute(
        select(MedicalHistory).where(
            MedicalHistory.id == history_id,
            MedicalHistory.patient_id == profile.id
        )
    )
    history = hist_result.scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="Medical history not found")

    await db.delete(history)
    return None


@router.delete("/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allergy(
    allergy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an allergy."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    allergy_result = await db.execute(
        select(Allergy).where(
            Allergy.id == allergy_id,
            Allergy.patient_id == profile.id
        )
    )
    allergy = allergy_result.scalar_one_or_none()
    if not allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")

    await db.delete(allergy)
    return None

