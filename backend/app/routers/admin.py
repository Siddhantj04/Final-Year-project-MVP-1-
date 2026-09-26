import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models.entities import Case, CaseStatus, User, UserRole
from app.schemas.cases import AdminMetricsResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetricsResponse)
def admin_metrics(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.admin)),
):
    settings = get_settings()
    metrics_path = Path(settings.metrics_json_path)
    metrics = {
        "accuracy": None,
        "precision": None,
        "recall": None,
        "specificity": None,
        "f1_score": None,
        "roc_auc": None,
        "confusion_matrix": None,
    }
    if metrics_path.is_file():
        try:
            loaded = json.loads(metrics_path.read_text(encoding="utf-8"))
            metrics.update({k: loaded.get(k) for k in metrics})
        except (json.JSONDecodeError, OSError):
            pass

    total_cases = db.query(func.count(Case.id)).scalar() or 0
    by_status = (
        db.query(Case.status, func.count(Case.id)).group_by(Case.status).all()
    )
    status_counts = {s.value: 0 for s in CaseStatus}
    for st, cnt in by_status:
        status_counts[st.value] = int(cnt)

    workflow_stats = {
        "total_cases": int(total_cases),
        "cases_by_status": status_counts,
        "pending_review": status_counts.get(CaseStatus.pending_review.value, 0),
        "approved": status_counts.get(CaseStatus.approved.value, 0),
        "rejected": status_counts.get(CaseStatus.rejected.value, 0),
    }

    return AdminMetricsResponse(**metrics, workflow_stats=workflow_stats)
