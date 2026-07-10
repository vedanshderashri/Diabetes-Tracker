import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import async_session_factory, engine
from app.models.report import MedicalReport, LabValue
from app.services.report_analyzer import report_analyzer
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reanalyze")

async def reanalyze():
    async with async_session_factory() as db:
        # Get all reports
        result = await db.execute(
            select(MedicalReport)
            .options(selectinload(MedicalReport.lab_values))
        )
        reports = result.scalars().all()
        
        logger.info(f"Found {len(reports)} reports in database.")
        
        updated_count = 0
        for report in reports:
            # Check if it was analyzed with fallback text or is missing summary
            if ("API configuration" in (report.ai_summary or "") or 
                "API configuration" in (report.ai_explanation or "") or 
                not report.ai_summary):
                
                if report.extracted_text:
                    logger.info(f"Re-analyzing report: {report.file_name} (ID: {report.id})")
                    try:
                        # Clear old lab values if any
                        for lv in report.lab_values:
                            await db.delete(lv)
                        
                        # Re-run AI analysis
                        analysis = await report_analyzer._analyze_report(report.extracted_text)
                        
                        report.report_type = analysis.get("report_type", "other")
                        report.ai_summary = analysis.get("summary", "")
                        report.ai_explanation = analysis.get("explanation", "")
                        report.critical_findings = analysis.get("critical_findings", "")
                        
                        # Add new lab values
                        lab_values = analysis.get("lab_values", [])
                        for lv in lab_values:
                            lab_value = LabValue(
                                id=str(uuid.uuid4()),
                                report_id=report.id,
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
                        updated_count += 1
                        logger.info(f"Successfully re-analyzed report: {report.file_name}")
                    except Exception as e:
                        logger.error(f"Failed to re-analyze report {report.id}: {e}")
        
        if updated_count > 0:
            await db.commit()
            logger.info(f"Successfully committed updates for {updated_count} reports.")
        else:
            logger.info("No reports needed re-analysis.")

if __name__ == "__main__":
    asyncio.run(reanalyze())
    # Clean up engine resources
    asyncio.run(engine.dispose())
