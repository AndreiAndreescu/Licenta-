from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "storage-service"
    DATABASE_URL: str = "postgresql+asyncpg://webintel:webintel@postgres:5432/webintel"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
