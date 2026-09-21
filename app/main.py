import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Header, HTTPException

from .config import settings
from .db import SessionLocal, init_db
from .handlers import router
from .models import Reminder
from sqlalchemy import select


if not settings.bot_token:
    print("WARNING: BOT_TOKEN is not set. The app can start for health checks, but Telegram polling/webhook will not work.")

bot = Bot(token=settings.bot_token or "000000:placeholder", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)
scheduler = AsyncIOScheduler(timezone=settings.timezone)
app = FastAPI(title="Fitness AI Telegram Bot")


async def check_reminders() -> None:
    now = datetime.now(ZoneInfo(settings.timezone))
    key = now.strftime("%Y-%m-%d %H:%M")
    async with SessionLocal() as session:
        result = await session.execute(select(Reminder).where(Reminder.enabled.is_(True), Reminder.reminder_time == now.strftime("%H:%M")))
        reminders = result.scalars().all()
        for reminder in reminders:
            if reminder.last_sent_key == key:
                continue
            messages = {
                "workout": "🏋️ Время тренировки! Сделай разминку и начни спокойно.",
                "food": "🍳 Время проверить питание. Не обязательно есть по часам, ориентируйся на голод и свой план.",
                "water": "💧 Напоминание о воде. Выпей стакан, если давно не пил.",
                "sleep": "🌙 Скоро пора готовиться ко сну. Убери яркий экран и начни спокойный вечерний ритуал.",
            }
            try:
                await bot.send_message(reminder.telegram_id, messages.get(reminder.kind, "🔔 Напоминание"))
                reminder.last_sent_key = key
            except Exception:
                pass
        await session.commit()


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    scheduler.add_job(check_reminders, "interval", minutes=1, id="reminder_tick", replace_existing=True)
    scheduler.start()
    if settings.webhook_url and settings.bot_token:
        await bot.set_webhook(url=f"{settings.webhook_url}/telegram/webhook", secret_token=settings.webhook_secret)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if settings.webhook_url and settings.bot_token:
        await bot.delete_webhook()
    await bot.session.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "ai_configured": bool(settings.deepseek_api_key), "database": bool(settings.database_url)}


@app.post("/telegram/webhook")
async def telegram_webhook(update: Update, x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict:
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="invalid webhook secret")
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.post("/scheduler/tick")
async def scheduler_tick(x_scheduler_secret: str | None = Header(default=None)) -> dict:
    if settings.scheduler_secret and x_scheduler_secret != settings.scheduler_secret:
        raise HTTPException(status_code=403, detail="invalid scheduler secret")
    await check_reminders()
    return {"ok": True}
