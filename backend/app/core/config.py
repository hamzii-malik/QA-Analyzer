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

    MAX_UPLOAD_SIZE_MB: int = 100
    MAX_EXTRACTED_SIZE_MB: int = 500
    MAX_EXTRACTED_FILES: int = 10000
    ANALYSIS_TIMEOUT: int = 1800
    FUZZ_CASES: int = 25
    FUZZ_MAX_STRING_LENGTH: int = 500
    ZAP_ENABLED: bool = False
    ZAP_PATH: str = ""
    ZAP_HOST: str = "127.0.0.1"
    ZAP_PORT: int = 8090
    FRONTEND_URL: str = "http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()