from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "WebIntel Monolith"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/webintel.db"
    MAX_CRAWL_DEPTH: int = 2
    MAX_PAGES_PER_JOB: int = 20
    CRAWL_DELAY_SECONDS: float = 1.0
    NLP_SUMMARY_SENTENCES: int = 3
    NLP_MAX_KEYWORDS: int = 10
    ALLOWED_DOMAINS: str = ""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
