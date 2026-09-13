from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    APP_NAME: str = "QA Analyzer"
    DEBUG: bool = True

    DATABASE_URL: str

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8001

    TARGET_PROJECTS_ROOT: str = ""
    REPORTS_DIR: str = ""
    SCREENSHOTS_DIR: str = ""

    LOG_LEVEL: str = "INFO"

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()