"""Create tables and seed admin + reviewer test accounts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models.entities import User, UserRole
from app.services.security import hash_password
from app.services.ml_inference import build_model
import torch

settings = get_settings()


def ensure_model_checkpoint():
    path = Path(settings.model_checkpoint_path)
    metrics_path = Path(settings.metrics_json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        model = build_model()
        torch.save({"model_state_dict": model.state_dict()}, path)
        print(f"Created placeholder model checkpoint at {path}")
    if not metrics_path.is_file():
        metrics_path.write_text(
            '{"accuracy":0.0,"precision":0.0,"recall":0.0,"specificity":0.0,'
            '"f1_score":0.0,"roc_auc":0.0,"confusion_matrix":[[0,0],[0,0]],'
            '"note":"Run scripts/train_model.py on RSNA data to populate metrics."}',
            encoding="utf-8",
        )
        print(f"Created placeholder metrics at {metrics_path}")


def seed_users():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == settings.seed_admin_email.lower()).first()
        if not admin:
            db.add(
                User(
                    email=settings.seed_admin_email.lower(),
                    hashed_password=hash_password(settings.seed_admin_password),
                    role=UserRole.admin,
                )
            )
            print(f"Seeded admin: {settings.seed_admin_email}")
        reviewer = db.query(User).filter(User.email == settings.seed_reviewer_email.lower()).first()
        if not reviewer:
            db.add(
                User(
                    email=settings.seed_reviewer_email.lower(),
                    hashed_password=hash_password(settings.seed_reviewer_password),
                    role=UserRole.reviewer,
                )
            )
            print(f"Seeded reviewer: {settings.seed_reviewer_email}")
        db.commit()
    finally:
        db.close()


def main():
    Base.metadata.create_all(bind=engine)
    ensure_model_checkpoint()
    seed_users()
    print("Seed complete.")


if __name__ == "__main__":
    main()
