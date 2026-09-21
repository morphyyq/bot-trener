import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_vision_model: str = os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-flash")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fitness_bot.db")
    webhook_url: str = os.getenv("WEBHOOK_URL", "").rstrip("/")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "change_me")
    timezone: str = os.getenv("TIMEZONE", "Europe/Moscow")
    scheduler_secret: str = os.getenv("SCHEDULER_SECRET", "change_me_scheduler")


settings = Settings()
