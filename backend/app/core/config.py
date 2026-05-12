from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "自动化测试平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/auto_test_platform"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Security
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_LOCK_DURATION_SECONDS: int = 3600

    # Task
    TASK_MAX_CONCURRENT: int = 50
    NODE_MAX_TASKS: int = 5

    # Node
    NODE_HEARTBEAT_INTERVAL: int = 30
    NODE_OFFLINE_THRESHOLD: int = 90

    # Log retention
    LOG_RETENTION_DAYS: int = 180
    RESULT_RETENTION_DAYS: int = 365

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
