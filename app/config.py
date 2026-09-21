import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # OpenRouter-compatible AI provider.
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv(
        "OPENROUTER_MODEL",
        "qwen/qwen3.8-27b:free",
    )
    openrouter_fallback_model: str = os.getenv(
        "OPENROUTER_FALLBACK_MODEL",
        "openrouter/free",
    )

    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./fitness_bot.db",
    )
    webhook_url: str = os.getenv("WEBHOOK_URL", "").rstrip("/")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "change_me")
    timezone: str = os.getenv("TIMEZONE", "Europe/Moscow")
    scheduler_secret: str = os.getenv(
        "SCHEDULER_SECRET",
        "change_me_scheduler",
    )


settings = Settings()
