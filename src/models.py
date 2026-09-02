"""Pydantic models for API request validation."""

from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    """Request body for /api/comparison (fast mode)."""

    doc_a_id: str | None = None
    doc_b_id: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    tender_id: str | None = None
    bid_ids: list[str] = Field(default_factory=list)
    chunk_size: int = Field(default=200, ge=50, le=2000)
    threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class AIComparisonRequest(BaseModel):
    """Request body for /api/comparison/ai (AI-assisted mode).

    API Key is NOT accepted from the client — it is read from
    server-side environment variables for security.
    """

    doc_a_id: str | None = None
    doc_b_id: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    tender_id: str | None = None
    bid_ids: list[str] = Field(default_factory=list)
    chunk_size: int = Field(default=200, ge=50, le=2000)
    threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    pre_filter: bool = Field(default=False, description='启用事前 AI 过滤（阶段1）')


class FileUploadResponse(BaseModel):
    """Response for /api/upload."""

    file_id: str
    filename: str
    doc_type: str
    label: str
    size_bytes: int
    size_mb: float
    chars: int
    status: str
    needs_split: bool
