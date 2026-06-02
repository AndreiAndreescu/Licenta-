from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "scheduler-service"
    REDIS_URL: str = "redis://redis:6379"
    STORAGE_URL: str = "http://storage:8001"
    LOG_LEVEL: str = "INFO"
    CONSUMER_GROUP: str = "scheduler-group"
    CONSUMER_NAME: str = "scheduler-1"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
