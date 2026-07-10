"""
MedAI Assistant - Reports API
Medical report upload, analysis, and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, log_audit_event
from app.core.config import get_settings
from app.models.user import User
from app.models.report import MedicalReport, LabValue
from app.services.report_analyzer import report_analyzer
from app.schemas.schemas import ReportResponse, ReportDetailResponse, LabValueResponse

router = APIRouter(prefix="/reports", tags=["Reports"])
settings = get_settings()

import tempfile
from pathlib import Path
import os

@router.post("/extract", status_code=status.HTTP_200_OK)
async def extract_document_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Statelessly extract text from PDF/Image in memory without writing to database."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = settings.ALLOWED_FILE_TYPES.split(",")
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(allowed)}",
        )

    content = await file.read()
    
    # Write to a temporary file
    fd, temp_path_str = tempfile.mkstemp(suffix=f".{ext}")
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        
        # Call report analyzer extraction method
        extracted_text = await report_analyzer._extract_text(temp_path, ext)
    finally:
        # Delete temporary file
        try:
            if temp_path.exists():
                os.remove(temp_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete temp file: {e}")

    return {"text": extracted_text or "", "file_name": file.filename}



@router.post("/upload", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and analyze a medical report (PDF, JPG, PNG)."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = settings.ALLOWED_FILE_TYPES.split(",")
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(allowed)}",
        )

    # Validate file size
    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Process and analyze
    report = await report_analyzer.process_upload(
        db, current_user.id, content, file.filename, ext
    )

    await log_audit_event(
        db, current_user.id, "upload_report", "report",
        details=f"Uploaded report: {file.filename}",
    )

    return ReportResponse.model_validate(report)


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reports for the current user."""
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.upload_date.desc())
    )
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed report with lab values."""
    result = await db.execute(
        select(MedicalReport)
        .options(selectinload(MedicalReport.lab_values))
        .where(
            MedicalReport.id == report_id,
            MedicalReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportDetailResponse(
        **ReportResponse.model_validate(report).model_dump(),
        lab_values=[LabValueResponse.model_validate(lv) for lv in report.lab_values],
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all medical reports (and files) for the current user."""
    result = await db.execute(
        select(MedicalReport).where(MedicalReport.user_id == current_user.id)
    )
    reports = result.scalars().all()

    import os
    for r in reports:
        if r.file_path:
            try:
                if os.path.exists(r.file_path):
                    os.remove(r.file_path)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to delete report file: {e}")
        await db.delete(r)

    await log_audit_event(
        db, current_user.id, "clear_all_reports", "report",
        details="Cleared all medical reports",
    )
    return None


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a medical report and its associated lab values."""
    result = await db.execute(
        select(MedicalReport)
        .where(
            MedicalReport.id == report_id,
            MedicalReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete file from filesystem if it exists
    if report.file_path:
        try:
            import os
            if os.path.exists(report.file_path):
                os.remove(report.file_path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to delete report file: {e}")

    await db.delete(report)
    await log_audit_event(
        db, current_user.id, "delete_report", "report",
        details=f"Deleted report: {report.file_name}",
    )
    await db.commit()

    return None
