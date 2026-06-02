from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "nlp-service"
    REDIS_URL: str = "redis://redis:6379"
    STORAGE_URL: str = "http://storage:8001"
    NLP_SUMMARY_SENTENCES: int = 3
    NLP_MAX_KEYWORDS: int = 10
    LOG_LEVEL: str = "INFO"
    CONSUMER_GROUP: str = "nlp-group"
    CONSUMER_NAME: str = "nlp-1"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
