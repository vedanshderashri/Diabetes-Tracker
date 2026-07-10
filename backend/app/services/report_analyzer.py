"""
MedAI Assistant - Medical Report Analyzer
PDF/Image processing, OCR, lab value extraction, and AI-powered analysis.
"""
import json
import logging
import uuid
import os
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.report import MedicalReport, LabValue

logger = logging.getLogger(__name__)
settings = get_settings()


class ReportAnalyzer:
    """Analyzes uploaded medical reports using OCR and AI."""

    async def process_upload(
        self,
        db: AsyncSession,
        user_id: str,
        file_content: bytes,
        file_name: str,
        file_type: str,
    ) -> MedicalReport:
        """
        Process an uploaded medical report.
        1. Save file
        2. Extract text (OCR for images, text extraction for PDFs)
        3. Analyze with AI
        4. Extract lab values
        5. Generate summary
        """
        # ── Save file ──
        report_id = str(uuid.uuid4())
        upload_dir = settings.upload_path / user_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_ext = file_type.lower()
        safe_name = f"{report_id}.{file_ext}"
        file_path = upload_dir / safe_name

        with open(file_path, "wb") as f:
            f.write(file_content)

        # Create report record
        report = MedicalReport(
            id=report_id,
            user_id=user_id,
            file_name=file_name,
            file_path=str(file_path),
            file_type=file_ext,
            file_size_bytes=len(file_content),
            status="processing",
        )
        db.add(report)
        await db.flush()

        # ── Extract text ──
        try:
            extracted_text = await self._extract_text(file_path, file_ext)
            report.extracted_text = extracted_text

            if extracted_text and extracted_text.strip():
                # ── AI Analysis ──
                analysis = await self._analyze_report(extracted_text)
                report.report_type = analysis.get("report_type", "other")
                report.ai_summary = analysis.get("summary", "")
                report.ai_explanation = analysis.get("explanation", "")
                report.critical_findings = analysis.get("critical_findings", "")

                # ── Extract Lab Values ──
                lab_values = analysis.get("lab_values", [])
                for lv in lab_values:
                    lab_value = LabValue(
                        id=str(uuid.uuid4()),
                        report_id=report_id,
                        test_name=lv.get("test_name", "Unknown"),
                        value=str(lv.get("value", "")),
                        unit=lv.get("unit", ""),
                        reference_range_low=lv.get("reference_low"),
                        reference_range_high=lv.get("reference_high"),
                        is_abnormal=lv.get("is_abnormal", False),
                        is_critical=lv.get("is_critical", False),
                        category=lv.get("category", ""),
                    )
                    db.add(lab_value)

                report.status = "analyzed"
                report.analyzed_at = datetime.now(timezone.utc)
            else:
                report.status = "error"
                report.ai_summary = "Could not extract text from the uploaded file."

        except Exception as e:
            logger.error(f"Report analysis failed: {e}")
            report.status = "error"
            report.ai_summary = f"Analysis failed: {str(e)}"

        await db.flush()
        return report

    async def _extract_text(self, file_path: Path, file_type: str) -> str:
        """Extract text from PDF or image file."""
        text = ""

        if file_type == "pdf":
            text = self._extract_pdf_text(file_path)
        elif file_type in ("jpg", "jpeg", "png"):
            text = self._extract_image_text(file_path)

        return text

    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()

            text = "\n".join(text_parts).strip()

            # If no text extracted (scanned PDF), try OCR on rendered images
            if not text:
                text = self._ocr_pdf(file_path)

            return text

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def _extract_image_text(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            from PIL import Image

            image = Image.open(file_path)

            try:
                import pytesseract
                text = pytesseract.image_to_string(image, lang="eng+hin")
            except Exception:
                # Fallback: return placeholder if tesseract not available
                logger.warning("Tesseract not available, using AI for image analysis")
                text = "[Image uploaded - text extraction pending AI analysis]"

            return text

        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return ""

    def _ocr_pdf(self, file_path: Path) -> str:
        """OCR a scanned PDF by rendering pages to images."""
        try:
            import fitz
            from PIL import Image
            import io

            doc = fitz.open(str(file_path))
            text_parts = []

            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))

                try:
                    import pytesseract
                    page_text = pytesseract.image_to_string(image, lang="eng+hin")
                    text_parts.append(page_text)
                except Exception:
                    text_parts.append("[OCR not available for this page]")

            doc.close()
            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            return ""

    async def _analyze_report(self, extracted_text: str) -> dict:
        """Use OpenAI to analyze the extracted report text."""
        if not settings.OPENAI_API_KEY:
            return self._fallback_analysis(extracted_text)

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

            analysis_prompt = f"""Analyze the following medical report text and provide a structured analysis.

REPORT TEXT:
{extracted_text[:4000]}

Respond with a JSON object containing:
{{
    "report_type": "blood_test|xray|mri|prescription|discharge_summary|other",
    "summary": "Brief 2-3 sentence summary of the report",
    "explanation": "Patient-friendly explanation of findings in simple language (3-5 sentences)",
    "critical_findings": "Any critical or urgent findings that need immediate attention (empty string if none)",
    "lab_values": [
        {{
            "test_name": "Test Name",
            "value": "numeric or text value",
            "unit": "unit of measurement",
            "reference_low": null or number,
            "reference_high": null or number,
            "is_abnormal": true/false,
            "is_critical": true/false,
            "category": "hematology|biochemistry|endocrine|lipid|liver|kidney|thyroid|other"
        }}
    ]
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting."""

            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical report analyzer. Extract structured data from medical reports accurately. Always return valid JSON.",
                    },
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            return json.loads(result_text)

        except Exception as e:
            logger.error(f"OpenAI report analysis failed: {e}")
            return self._fallback_analysis(extracted_text)

    def _fallback_analysis(self, text: str) -> dict:
        """Generate a basic analysis when AI is unavailable."""
        # Simple keyword-based detection
        text_lower = text.lower()

        report_type = "other"
        if any(kw in text_lower for kw in ["hemoglobin", "wbc", "rbc", "platelet", "cbc"]):
            report_type = "blood_test"
        elif any(kw in text_lower for kw in ["x-ray", "xray", "radiograph"]):
            report_type = "xray"
        elif any(kw in text_lower for kw in ["mri", "magnetic resonance"]):
            report_type = "mri"
        elif any(kw in text_lower for kw in ["prescription", "rx", "tab.", "capsule"]):
            report_type = "prescription"

        return {
            "report_type": report_type,
            "summary": "Report text has been extracted. Detailed AI analysis requires API configuration.",
            "explanation": "The medical report has been uploaded and text has been extracted successfully. "
                          "Please configure the OpenAI API key for detailed AI-powered analysis.",
            "critical_findings": "",
            "lab_values": [],
        }


# Singleton instance
report_analyzer = ReportAnalyzer()
