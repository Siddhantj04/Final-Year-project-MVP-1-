import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models.entities import AIAnalysis, Case, CaseStatus, QualityStatus, Report, User, UserRole
from app.schemas.cases import (
    AnalyzeResponse,
    CaseDetail,
    CaseSummary,
    QualityCheckResponse,
    ReportResponse,
)
from app.services.image_quality import check_image_quality, quality_details_to_json
from app.services.ml_inference import predict_and_gradcam
from app.services.report_template import DISCLAIMER, HEATMAP_NOTICE, build_template_report
from app.utils.file_validation import validate_image_file

router = APIRouter(prefix="/cases", tags=["cases"])


def _case_to_summary(case: Case) -> CaseSummary:
    pred = None
    conf = None
    if case.ai_analysis:
        pred = case.ai_analysis.predicted_class
        conf = case.ai_analysis.confidence
    return CaseSummary(
        id=case.id,
        status=case.status.value,
        quality_status=case.quality_status.value if case.quality_status else None,
        original_filename=case.original_filename,
        created_at=case.created_at.isoformat() if case.created_at else "",
        predicted_class=pred,
        confidence=conf,
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_case(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )
    valid, err = validate_image_file(file.filename, content)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    ext = Path(file.filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(content)

    case = Case(
        uploader_id=user.id,
        original_filename=file.filename,
        stored_path=str(stored_path),
        status=CaseStatus.uploaded,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"case_id": case.id, "message": "Upload successful.", "original_filename": case.original_filename}


@router.post("/{case_id}/quality-check", response_model=QualityCheckResponse)
def quality_check(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")
    details = check_image_quality(case.stored_path)
    case.quality_status = QualityStatus(details["suitability"])
    case.quality_details_json = quality_details_to_json(details)
    case.status = CaseStatus.quality_checked
    db.commit()
    return QualityCheckResponse(case_id=case_id, **details)


@router.post("/{case_id}/analyze", response_model=AnalyzeResponse)
def analyze_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    settings = get_settings()
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")
    if case.quality_status is None:
        raise HTTPException(status_code=400, detail="Run quality check before analysis.")
    if case.quality_status == QualityStatus.unsuitable:
        raise HTTPException(
            status_code=400,
            detail="Analysis is not allowed for unsuitable images. Re-upload a better quality image.",
        )

    heatmap_name = f"heatmap_{case_id}_{uuid.uuid4().hex[:8]}.png"
    heatmap_path = Path(settings.heatmap_dir) / heatmap_name
    predicted_class, confidence = predict_and_gradcam(case.stored_path, str(heatmap_path))

    if case.ai_analysis:
        db.delete(case.ai_analysis)
        db.flush()
    analysis = AIAnalysis(
        case_id=case.id,
        predicted_class=predicted_class,
        confidence=confidence,
        heatmap_path=str(heatmap_path),
    )
    db.add(analysis)
    case.status = CaseStatus.analyzed
    db.commit()

    return AnalyzeResponse(
        case_id=case_id,
        predicted_class=predicted_class,
        confidence=confidence,
        heatmap_url=f"/cases/{case_id}/heatmap",
        heatmap_notice=HEATMAP_NOTICE,
    )


@router.get("/{case_id}/report", response_model=ReportResponse)
def get_report(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")
    if case.ai_analysis is None:
        raise HTTPException(status_code=400, detail="Analysis must be completed before generating a report.")

    quality_messages: list[str] = []
    quality_status = case.quality_status.value if case.quality_status else "unknown"
    if case.quality_details_json:
        try:
            qd = json.loads(case.quality_details_json)
            quality_messages = qd.get("messages", [])
            quality_status = qd.get("suitability", quality_status)
        except json.JSONDecodeError:
            pass

    template = build_template_report(
        case.ai_analysis.predicted_class,
        case.ai_analysis.confidence,
        quality_status,
        quality_messages,
    )
    if case.report:
        case.report.template_text = template
    else:
        case.report = Report(case_id=case.id, template_text=template)
        db.add(case.report)
    case.status = CaseStatus.pending_review
    db.commit()

    display_text = case.report.reviewer_edited_text or case.report.template_text
    return ReportResponse(case_id=case_id, template_text=display_text, disclaimer=DISCLAIMER)


@router.get("", response_model=list[CaseSummary])
def list_cases(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    query = db.query(Case).order_by(Case.created_at.desc())
    if user.role == UserRole.reviewer:
        query = query.filter(Case.uploader_id == user.id)
    cases = query.all()
    return [_case_to_summary(c) for c in cases]


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")

    quality_details = None
    if case.quality_details_json:
        try:
            quality_details = json.loads(case.quality_details_json)
        except json.JSONDecodeError:
            quality_details = None

    report_text = None
    if case.report:
        report_text = case.report.reviewer_edited_text or case.report.template_text

    return CaseDetail(
        id=case.id,
        status=case.status.value,
        quality_status=case.quality_status.value if case.quality_status else None,
        original_filename=case.original_filename,
        image_url=f"/cases/{case_id}/image",
        heatmap_url=f"/cases/{case_id}/heatmap" if case.ai_analysis else None,
        predicted_class=case.ai_analysis.predicted_class if case.ai_analysis else None,
        confidence=case.ai_analysis.confidence if case.ai_analysis else None,
        report_text=report_text,
        quality_details=quality_details,
    )


@router.get("/{case_id}/image")
def get_case_image(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")
    path = Path(case.stored_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found.")
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media)


@router.get("/{case_id}/heatmap")
def get_case_heatmap(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot access this case.")
    if case.ai_analysis is None:
        raise HTTPException(status_code=404, detail="Heatmap not available.")
    path = Path(case.ai_analysis.heatmap_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Heatmap file not found.")
    return FileResponse(path, media_type="image/png")
