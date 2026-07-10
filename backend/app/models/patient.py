"""
MedAI Assistant - Patient Models
Patient health profile, medical history, medications, allergies, chronic conditions.
"""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Date, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=True)  # male | female | other
    blood_type: Mapped[str] = mapped_column(String(5), nullable=True)
    height_cm: Mapped[float] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=True)
    emergency_contact_name: Mapped[str] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="patient_profile")
    medical_history = relationship("MedicalHistory", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    chronic_conditions = relationship("ChronicCondition", back_populates="patient", cascade="all, delete-orphan")


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_profiles.id"), nullable=False
    )
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    diagnosed_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active | resolved | managed
    treating_doctor: Mapped[str] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient = relationship("PatientProfile", back_populates="medical_history")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_profiles.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str] = mapped_column(String(100), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    prescribed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient = relationship("PatientProfile", back_populates="medications")


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_profiles.id"), nullable=False
    )
    allergen: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default="moderate"
    )  # mild | moderate | severe
    reaction: Mapped[str] = mapped_column(Text, nullable=True)
    diagnosed_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient = relationship("PatientProfile", back_populates="allergies")


class ChronicCondition(Base):
    __tablename__ = "chronic_conditions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_profiles.id"), nullable=False
    )
    condition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="moderate")
    diagnosed_date: Mapped[date] = mapped_column(Date, nullable=True)
    management_plan: Mapped[str] = mapped_column(Text, nullable=True)
    last_checkup: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient = relationship("PatientProfile", back_populates="chronic_conditions")
