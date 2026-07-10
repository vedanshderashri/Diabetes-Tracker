"""
MedAI Assistant - Doctor Summary Generator
AI-powered clinical summary generation for healthcare providers.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.user import User
from app.models.patient import PatientProfile, MedicalHistory, Medication, Allergy, ChronicCondition
from app.models.chat import ChatSession, ChatMessage
from app.models.report import MedicalReport, LabValue

logger = logging.getLogger(__name__)
settings = get_settings()


class DoctorSummaryGenerator:
    """Generates concise clinical summaries for healthcare providers."""

    async def generate_summary(
        self,
        db: AsyncSession,
        user_id: str,
        include_reports: bool = True,
        include_chat_history: bool = True,
    ) -> dict:
        """Generate a comprehensive clinical summary for a patient."""

        # ── Gather Patient Data ──
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("Patient not found")

        profile_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        # Demographics
        demographics = {
            "name": user.full_name,
            "email": user.email,
            "gender": profile.gender if profile else "Not specified",
            "date_of_birth": str(profile.date_of_birth) if profile and profile.date_of_birth else "Not specified",
            "blood_type": profile.blood_type if profile else "Not specified",
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
        }

        # BMI calculation
        if profile and profile.height_cm and profile.weight_kg:
            height_m = profile.height_cm / 100
            demographics["bmi"] = round(profile.weight_kg / (height_m * height_m), 1)

        # Medical History
        history_items = []
        if profile:
            history_result = await db.execute(
                select(MedicalHistory).where(MedicalHistory.patient_id == profile.id)
            )
            for h in history_result.scalars().all():
                history_items.append({
                    "condition": h.condition,
                    "status": h.status,
                    "diagnosed_date": str(h.diagnosed_date) if h.diagnosed_date else None,
                })

        # Medications
        medications_list = []
        if profile:
            med_result = await db.execute(
                select(Medication).where(Medication.patient_id == profile.id)
            )
            for m in med_result.scalars().all():
                medications_list.append({
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "is_active": m.is_active,
                })

        # Allergies
        allergies_list = []
        if profile:
            allergy_result = await db.execute(
                select(Allergy).where(Allergy.patient_id == profile.id)
            )
            allergies_list = [a.allergen for a in allergy_result.scalars().all()]

        # Chronic Conditions
        chronic_list = []
        if profile:
            chronic_result = await db.execute(
                select(ChronicCondition).where(ChronicCondition.patient_id == profile.id)
            )
            for c in chronic_result.scalars().all():
                chronic_list.append({
                    "condition": c.condition_name,
                    "severity": c.severity,
                })

        # Lab Abnormalities
        lab_abnormalities = []
        if include_reports:
            lab_result = await db.execute(
                select(LabValue)
                .join(MedicalReport)
                .where(
                    MedicalReport.user_id == user_id,
                    LabValue.is_abnormal == True,
                )
                .order_by(LabValue.created_at.desc())
                .limit(20)
            )
            for lv in lab_result.scalars().all():
                lab_abnormalities.append({
                    "test": lv.test_name,
                    "value": f"{lv.value} {lv.unit or ''}".strip(),
                    "reference": f"{lv.reference_range_low}-{lv.reference_range_high}" if lv.reference_range_low else "N/A",
                    "is_critical": lv.is_critical,
                })

        # Chief Complaints from Chat
        chief_complaints = []
        symptom_timeline = []
        if include_chat_history:
            chat_result = await db.execute(
                select(ChatMessage)
                .join(ChatSession)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
            )
            for msg in chat_result.scalars().all():
                chief_complaints.append(msg.content[:200])
                symptom_timeline.append({
                    "date": str(msg.created_at),
                    "complaint": msg.content[:200],
                })

        # ── Generate AI Narrative ──
        narrative = await self._generate_narrative(
            demographics, history_items, medications_list,
            allergies_list, chronic_list, lab_abnormalities,
            chief_complaints
        )

        # Recommended next steps
        next_steps = self._generate_next_steps(
            lab_abnormalities, chronic_list, chief_complaints
        )

        return {
            "patient_name": user.full_name,
            "summary_date": datetime.now(timezone.utc),
            "demographics": demographics,
            "chief_complaints": chief_complaints[:5],
            "symptom_timeline": symptom_timeline[:10],
            "lab_abnormalities": lab_abnormalities,
            "potential_conditions": [
                {"condition": c["condition"], "severity": c["severity"]}
                for c in chronic_list
            ],
            "current_medications": medications_list,
            "allergies": allergies_list,
            "recommended_next_steps": next_steps,
            "ai_generated_narrative": narrative,
        }

    async def _generate_narrative(
        self, demographics, history, medications, allergies,
        chronic, lab_abnormalities, complaints
    ) -> str:
        """Generate an AI-powered clinical narrative."""
        if not settings.OPENAI_API_KEY:
            return self._fallback_narrative(demographics, chronic, lab_abnormalities)

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

            prompt = f"""Generate a concise clinical summary for a healthcare provider based on the following patient data:

DEMOGRAPHICS: {json.dumps(demographics)}
MEDICAL HISTORY: {json.dumps(history)}
CURRENT MEDICATIONS: {json.dumps(medications)}
ALLERGIES: {json.dumps(allergies)}
CHRONIC CONDITIONS: {json.dumps(chronic)}
ABNORMAL LAB VALUES: {json.dumps(lab_abnormalities)}
RECENT COMPLAINTS: {json.dumps(complaints[:5])}

Write a professional, concise clinical summary (3-5 paragraphs) suitable for a physician review.
Include key findings, relevant history, and areas requiring attention.
Do NOT provide diagnoses — summarize objectively."""

            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a clinical documentation specialist. Write concise, professional medical summaries."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return self._fallback_narrative(demographics, chronic, lab_abnormalities)

    def _fallback_narrative(self, demographics, chronic, lab_abnormalities) -> str:
        """Generate a template-based narrative when AI is unavailable."""
        parts = [f"Patient: {demographics.get('name', 'Unknown')}"]

        if demographics.get('gender'):
            parts.append(f"Gender: {demographics['gender']}")
        if demographics.get('bmi'):
            parts.append(f"BMI: {demographics['bmi']}")

        if chronic:
            conditions = ", ".join(c["condition"] for c in chronic)
            parts.append(f"\nChronic Conditions: {conditions}")

        if lab_abnormalities:
            parts.append(f"\nAbnormal Lab Values: {len(lab_abnormalities)} findings noted.")
            critical = [l for l in lab_abnormalities if l.get("is_critical")]
            if critical:
                parts.append(f"Critical values: {len(critical)} require immediate attention.")

        return "\n".join(parts)

    def _generate_next_steps(self, lab_abnormalities, chronic, complaints) -> list:
        """Generate recommended next steps."""
        steps = []

        if lab_abnormalities:
            critical = [l for l in lab_abnormalities if l.get("is_critical")]
            if critical:
                steps.append("URGENT: Review critical lab values and consider immediate intervention")
            steps.append("Follow up on abnormal lab results")

        if chronic:
            steps.append("Review chronic condition management plans")

        if complaints:
            steps.append("Address patient's recent complaints and symptoms")

        steps.extend([
            "Update medication list if needed",
            "Schedule follow-up appointment",
        ])

        return steps[:6]


# Singleton instance
doctor_summary_generator = DoctorSummaryGenerator()
