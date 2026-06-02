from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "crawler-service"
    REDIS_URL: str = "redis://redis:6379"
    STORAGE_URL: str = "http://storage:8001"
    CRAWL_DELAY_SECONDS: float = 0.5
    MAX_CONCURRENT_REQUESTS: int = 8
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    LOG_LEVEL: str = "INFO"
    CONSUMER_GROUP: str = "crawler-group"
    CONSUMER_NAME: str = "crawler-1"
    HTML_TTL_SECONDS: int = 3600

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
