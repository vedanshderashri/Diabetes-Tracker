"""
MedAI Assistant - Health Score Calculator
Composite health score based on patient data and reports.
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.patient import PatientProfile, MedicalHistory, Medication, Allergy, ChronicCondition
from app.models.report import MedicalReport, LabValue

logger = logging.getLogger(__name__)


class HealthScoreCalculator:
    """Calculates a composite health score (0-100) for patients."""

    async def calculate(self, db: AsyncSession, user_id: str) -> dict:
        """
        Calculate health score based on:
        - Lab values normality
        - Chronic conditions count
        - Active medications
        - Recent report trends
        - Profile completeness
        """
        # Enforce health score must be 0 until patient adds their report
        reports_count_result = await db.execute(
            select(func.count(MedicalReport.id)).where(MedicalReport.user_id == user_id)
        )
        reports_count = reports_count_result.scalar() or 0

        if reports_count == 0:
            return {
                "overall_score": 0,
                "category": "needs_attention",
                "breakdown": {
                    "profile_completeness": 0,
                    "lab_values": 0,
                    "chronic_conditions": 0,
                    "medications": 0,
                    "recent_activity": 0
                },
                "recommendations": ["Upload your first medical report to calculate your health score"],
            }

        scores = {}
        recommendations = []


        # ── Profile Score (0-15) ──
        profile = await self._get_profile(db, user_id)
        profile_score = self._score_profile_completeness(profile)
        scores["profile_completeness"] = profile_score

        if profile_score < 10:
            recommendations.append("Complete your health profile for more accurate assessments")

        # ── Lab Values Score (0-35) ──
        lab_score, lab_recs = await self._score_lab_values(db, user_id)
        scores["lab_values"] = lab_score
        recommendations.extend(lab_recs)

        # ── Chronic Conditions Score (0-20) ──
        chronic_score, chronic_recs = await self._score_chronic_conditions(db, profile)
        scores["chronic_conditions"] = chronic_score
        recommendations.extend(chronic_recs)

        # ── Medication Management Score (0-15) ──
        med_score = await self._score_medications(db, profile)
        scores["medications"] = med_score

        # ── Recent Activity Score (0-15) ──
        activity_score = await self._score_recent_activity(db, user_id)
        scores["recent_activity"] = activity_score

        if activity_score < 10:
            recommendations.append("Upload recent medical reports for better health tracking")

        # ── Calculate Overall ──
        overall = sum(scores.values())
        overall = max(0, min(100, overall))

        # Determine category
        if overall >= 80:
            category = "excellent"
        elif overall >= 60:
            category = "good"
        elif overall >= 40:
            category = "fair"
        else:
            category = "needs_attention"

        if not recommendations:
            recommendations.append("Keep up the great work maintaining your health!")

        return {
            "overall_score": overall,
            "category": category,
            "breakdown": scores,
            "recommendations": recommendations[:5],  # Top 5 recommendations
        }

    async def _get_profile(self, db: AsyncSession, user_id: str) -> Optional[PatientProfile]:
        result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def _score_profile_completeness(self, profile: Optional[PatientProfile]) -> int:
        if not profile:
            return 0

        score = 0
        if profile.date_of_birth:
            score += 3
        if profile.gender:
            score += 2
        if profile.blood_type:
            score += 2
        if profile.height_cm:
            score += 2
        if profile.weight_kg:
            score += 2
        if profile.emergency_contact_name:
            score += 2
        if profile.emergency_contact_phone:
            score += 2
        return min(score, 15)

    async def _score_lab_values(self, db: AsyncSession, user_id: str) -> tuple:
        """Score based on recent lab values."""
        # Get lab values from recent reports (last 90 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await db.execute(
            select(LabValue)
            .join(MedicalReport)
            .where(
                MedicalReport.user_id == user_id,
                MedicalReport.upload_date >= cutoff,
            )
        )
        lab_values = result.scalars().all()

        recommendations = []

        if not lab_values:
            return 25, ["Consider getting a regular health check-up with blood work"]

        total = len(lab_values)
        normal = sum(1 for lv in lab_values if not lv.is_abnormal)
        critical = sum(1 for lv in lab_values if lv.is_critical)

        if critical > 0:
            recommendations.append(
                f"⚠️ {critical} critical lab value(s) detected - consult your doctor immediately"
            )

        abnormal = total - normal
        if abnormal > 0:
            recommendations.append(
                f"{abnormal} lab value(s) outside normal range - discuss with your healthcare provider"
            )

        # Score: full marks if all normal, decreasing with abnormalities
        normality_ratio = normal / total if total > 0 else 0.5
        score = int(normality_ratio * 35)

        # Penalty for critical values
        score -= critical * 5
        return max(0, min(35, score)), recommendations

    async def _score_chronic_conditions(
        self, db: AsyncSession, profile: Optional[PatientProfile]
    ) -> tuple:
        if not profile:
            return 18, []

        result = await db.execute(
            select(ChronicCondition).where(ChronicCondition.patient_id == profile.id)
        )
        conditions = result.scalars().all()

        recommendations = []

        if not conditions:
            return 20, []

        # Fewer chronic conditions = higher score
        count = len(conditions)
        if count <= 1:
            score = 16
        elif count <= 2:
            score = 12
        elif count <= 3:
            score = 8
        else:
            score = 4
            recommendations.append("Multiple chronic conditions detected - regular monitoring recommended")

        # Check for recent checkups
        for condition in conditions:
            if condition.last_checkup:
                days_since = (datetime.now().date() - condition.last_checkup).days
                if days_since > 180:
                    recommendations.append(
                        f"Schedule a follow-up for {condition.condition_name} (last checkup > 6 months ago)"
                    )

        return min(20, score), recommendations

    async def _score_medications(
        self, db: AsyncSession, profile: Optional[PatientProfile]
    ) -> int:
        if not profile:
            return 12

        result = await db.execute(
            select(Medication).where(
                Medication.patient_id == profile.id, Medication.is_active == True
            )
        )
        active_meds = result.scalars().all()

        if not active_meds:
            return 15  # No medications = good (assuming no chronic conditions)

        # Having tracked medications is good
        return 12

    async def _score_recent_activity(self, db: AsyncSession, user_id: str) -> int:
        """Score based on recent health engagement."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        # Count recent reports
        result = await db.execute(
            select(func.count(MedicalReport.id)).where(
                MedicalReport.user_id == user_id,
                MedicalReport.upload_date >= cutoff,
            )
        )
        recent_reports = result.scalar() or 0

        score = 5  # Base score for having an account
        if recent_reports > 0:
            score += 5
        if recent_reports >= 2:
            score += 5

        return min(15, score)


# Singleton instance
health_score_calculator = HealthScoreCalculator()
