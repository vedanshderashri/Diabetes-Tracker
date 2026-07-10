"""
MedAI Assistant - Report Models
Medical reports, lab values, and AI-generated summaries.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | jpg | png
    file_size_bytes: Mapped[int] = mapped_column(nullable=True)
    report_type: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # blood_test | xray | mri | prescription | other
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    critical_findings: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="uploaded"
    )  # uploaded | processing | analyzed | error
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="medical_reports")
    lab_values = relationship(
        "LabValue",
        back_populates="report",
        cascade="all, delete-orphan",
    )


class LabValue(Base):
    __tablename__ = "lab_values"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("medical_reports.id"), nullable=False
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_range_low: Mapped[float] = mapped_column(Float, nullable=True)
    reference_range_high: Mapped[float] = mapped_column(Float, nullable=True)
    is_abnormal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    report = relationship("MedicalReport", back_populates="lab_values")
