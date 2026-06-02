from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from pydantic import computed_field


class JobCreate(BaseModel):
    query: str = Field(..., min_length=3)
    max_depth: int = Field(2, ge=1, le=5)
    max_pages: int = Field(20, ge=1, le=50)
    seed_urls: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: int
    query: str
    seed_urls: list[str] | None = None
    status: str
    max_depth: int
    max_pages: int
    created_at: datetime
    updated_at: datetime
    pages_crawled: int
    pages_analyzed: int
    error_message: str | None = None
    verdict: str | None = None
    verdict_confidence: int | None = None
    verdict_evidence: str | None = None

    @computed_field
    def progress_pct(self) -> int:
        if self.max_pages <= 0:
            return 0
        return min(100, int((self.pages_analyzed / self.max_pages) * 100))


class PageResponse(BaseModel):
    id: int
    job_id: int
    url: str
    title: str | None = None
    http_status: int | None = None
    fetched_at: datetime
    clean_text: str | None = None
    language: str | None = None


class AnalysisResponse(BaseModel):
    id: int
    page_id: int
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    entities: dict[str, list[str]] = Field(default_factory=dict)


class PageWithAnalysis(PageResponse):
    analysis: AnalysisResponse | None = None


class JobResultsResponse(JobResponse):
    pages: list[PageWithAnalysis] = Field(default_factory=list)
