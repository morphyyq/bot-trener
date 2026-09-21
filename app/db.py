from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, DailyStat, FoodEntry, UserProfile


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


engine = create_async_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_profile(session: AsyncSession, telegram_id: int) -> UserProfile | None:
    return await session.get(UserProfile, telegram_id)


async def get_or_create_daily(session: AsyncSession, telegram_id: int, day: date) -> DailyStat:
    result = await session.execute(
        select(DailyStat).where(DailyStat.telegram_id == telegram_id, DailyStat.stat_date == day)
    )
    daily = result.scalar_one_or_none()
    if daily is None:
        daily = DailyStat(telegram_id=telegram_id, stat_date=day)
        session.add(daily)
        await session.flush()
    return daily


async def nutrition_totals(session: AsyncSession, telegram_id: int, day: date) -> dict[str, float]:
    result = await session.execute(
        select(
            func.coalesce(func.sum(FoodEntry.calories), 0),
            func.coalesce(func.sum(FoodEntry.protein_g), 0),
            func.coalesce(func.sum(FoodEntry.fat_g), 0),
            func.coalesce(func.sum(FoodEntry.carbs_g), 0),
        ).where(FoodEntry.telegram_id == telegram_id, func.date(FoodEntry.eaten_at) == day)
    )
    calories, protein, fat, carbs = result.one()
    return {
        "calories": float(calories or 0),
        "protein": float(protein or 0),
        "fat": float(fat or 0),
        "carbs": float(carbs or 0),
    }
