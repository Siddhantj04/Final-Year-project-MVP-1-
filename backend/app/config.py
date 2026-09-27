from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    database_url: str = "postgresql://radiologylearn:Siddhant@24@localhost:5432/radiologylearn"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480
    environment: str = "development"
    frontend_origin: str = "http://localhost:3000"
    max_upload_size_mb: int = 10
    model_checkpoint_path: str = "/app/models/best_model.pt"
    metrics_json_path: str = "/app/models/metrics.json"
    upload_dir: str = "/app/uploads"
    heatmap_dir: str = "/app/heatmaps"

    seed_admin_email: str = "admin@radiologylearn.local"
    seed_admin_password: str = "AdminTest123!"
    seed_reviewer_email: str = "reviewer@radiologylearn.local"
    seed_reviewer_password: str = "ReviewerTest123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
