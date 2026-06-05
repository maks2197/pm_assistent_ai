from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    # YouGile
    YOUGILE_API_KEY: str = ""
    YOUGILE_BASE_URL: str = "https://ru.yougile.com/api-v2"
    YOUGILE_BOARD_ID: str = ""

    # AI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Yandex SpeechKit
    YANDEX_SPEECHKIT_API_KEY: str = ""
    YANDEX_FOLDER_ID: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://pmassistant:secret@db:5432/pmassistant"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # App
    SECRET_KEY: str = "supersecret"
    ENV: str = "development"
    DEBUG: bool = False

    # Evening sync
    EVENING_SYNC_HOUR: int = 18  # 18:00
    EVENING_SYNC_MINUTE: int = 0

    # Reminders
    REMINDER_CHECK_INTERVAL: int = 300  # 5 min

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
