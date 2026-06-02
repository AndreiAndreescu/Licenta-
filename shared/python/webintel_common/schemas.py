from pydantic import BaseModel, Field, field_validator
from typing import Any


class JobCreatedEvent(BaseModel):
    job_id: int
    query: str
    seed_urls: list[str]
    max_depth: int
    max_pages: int


class PageCrawledEvent(BaseModel):
    job_id: int
    page_id: int
    url: str
    html_redis_key: str


class PageExtractedEvent(BaseModel):
    job_id: int
    page_id: int


class PageAnalyzedEvent(BaseModel):
    job_id: int
    page_id: int


class JobCrawlFinishedEvent(BaseModel):
    job_id: int
    total_pages_crawled: int


class JobCompletedEvent(BaseModel):
    job_id: int


class JobCreateRequest(BaseModel):
    query: str
    seed_urls: list[str] = Field(default_factory=list)
    max_depth: int = 2
    max_pages: int = 20


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    pages_crawled: int
    pages_analyzed: int
    progress_pct: int
    error_message: str | None = None


class PageCreateRequest(BaseModel):
    url: str
    title: str | None = None
    http_status: int | None = None
    fetched_at: str | None = None
    language: str | None = None


class PageResponse(BaseModel):
    id: int
    job_id: int
    url: str
    title: str | None = None
    http_status: int | None = None
    fetched_at: str | None = None
    language: str | None = None


class ExtractionCreate(BaseModel):
    clean_text: str
    author: str | None = None
    publish_date: str | None = None


class ExtractionResponse(ExtractionCreate):
    id: int
    page_id: int


class AnalysisCreate(BaseModel):
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    entities: dict[str, list[str]] = Field(default_factory=dict)


class AnalysisResponse(AnalysisCreate):
    id: int
    page_id: int

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:
                return []
        return value or []

    @field_validator("entities", mode="before")
    @classmethod
    def parse_entities(cls, value: Any) -> dict[str, list[str]]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:
                return {}
        return value or {}


class JobResultsResponse(BaseModel):
    job: JobStatusResponse
    pages: list[PageResponse] = Field(default_factory=list)
