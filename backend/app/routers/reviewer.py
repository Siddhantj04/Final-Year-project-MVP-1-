from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_roles
from app.models.entities import AuditLog, Case, CaseStatus, User, UserRole
from app.schemas.cases import ReviewActionRequest

router = APIRouter(prefix="/reviewer", tags=["reviewer"])

VALID_ACTIONS = {
    "approve": CaseStatus.approved,
    "edit": CaseStatus.edited,
    "reject": CaseStatus.rejected,
    "unsuitable": CaseStatus.unsuitable,
}


@router.post("/cases/{case_id}/decision")
def reviewer_decision(
    case_id: int,
    body: ReviewActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.reviewer, UserRole.admin)),
):
    action = body.action.lower().strip()
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Use approve, edit, reject, or unsuitable.",
        )
    if action == "edit" and (body.edited_report_text is None or not body.edited_report_text.strip()):
        raise HTTPException(status_code=400, detail="Edited report text is required when action is edit.")

    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.uploader_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="You cannot review this case.")
    if case.report is None and action in ("approve", "edit", "reject"):
        raise HTTPException(status_code=400, detail="Generate a report before submitting a review decision.")

    new_status = VALID_ACTIONS[action]
    case.status = new_status

    if action == "edit" and case.report and body.edited_report_text:
        case.report.reviewer_edited_text = body.edited_report_text.strip()

    log = AuditLog(
        case_id=case.id,
        reviewer_id=user.id,
        action=action,
        details=body.edited_report_text[:500] if body.edited_report_text else None,
    )
    db.add(log)
    db.commit()
    return {"case_id": case_id, "status": case.status.value, "message": f"Case marked as {case.status.value}."}
