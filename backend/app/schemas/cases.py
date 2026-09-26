from pydantic import BaseModel, Field


class QualityCheckResponse(BaseModel):
    case_id: int
    suitability: str
    blur_variance: float
    brightness_mean: float
    contrast_std: float
    width: int
    height: int
    messages: list[str]


class AnalyzeResponse(BaseModel):
    case_id: int
    predicted_class: str
    confidence: float
    heatmap_url: str
    heatmap_notice: str


class ReportResponse(BaseModel):
    case_id: int
    template_text: str
    disclaimer: str


class CaseSummary(BaseModel):
    id: int
    status: str
    quality_status: str | None
    original_filename: str
    created_at: str
    predicted_class: str | None = None
    confidence: float | None = None

    model_config = {"from_attributes": True}


class CaseDetail(BaseModel):
    id: int
    status: str
    quality_status: str | None
    original_filename: str
    image_url: str
    heatmap_url: str | None
    predicted_class: str | None
    confidence: float | None
    report_text: str | None
    quality_details: dict | None


class ReviewActionRequest(BaseModel):
    action: str = Field(description="approve | edit | reject | unsuitable")
    edited_report_text: str | None = Field(default=None, max_length=20000)


class AdminMetricsResponse(BaseModel):
    accuracy: float | None
    precision: float | None
    recall: float | None
    specificity: float | None
    f1_score: float | None
    roc_auc: float | None
    confusion_matrix: list[list[int]] | None
    workflow_stats: dict
