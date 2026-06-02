from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "gateway-service"
    SCHEDULER_URL: str = "http://scheduler:8005"
    STORAGE_URL: str = "http://storage:8001"
    DASHBOARD_ORIGIN: str = "http://localhost:3000"
    RATE_LIMIT: str = "60/minute"
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
