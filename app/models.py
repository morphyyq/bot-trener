from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(40), default="не указано")
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    goal: Mapped[str] = mapped_column(String(120), default="поддерживать форму")
    activity_level: Mapped[str] = mapped_column(String(120), default="средний")
    workouts_per_week: Mapped[int] = mapped_column(Integer, default=3)
    sleep_time: Mapped[str] = mapped_column(String(10), default="23:00")
    wake_time: Mapped[str] = mapped_column(String(10), default="07:00")
    equipment: Mapped[str] = mapped_column(String(250), default="без оборудования")
    plan_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FoodEntry(Base):
    __tablename__ = "food_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    eaten_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    description: Mapped[str] = mapped_column(Text)
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(30), default="text")


class DailyStat(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint("telegram_id", "stat_date", name="uq_daily_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    water_ml: Mapped[int] = mapped_column(Integer, default=0)
    sleep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    workout_done: Mapped[bool] = mapped_column(Boolean, default=False)
    xp: Mapped[int] = mapped_column(Integer, default=0)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    exercises_json: Mapped[str] = mapped_column(Text, default="[]")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class BodyWeight(Base):
    __tablename__ = "body_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("telegram_id", "kind", name="uq_reminder_user_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(30))
    reminder_time: Mapped[str] = mapped_column(String(5), default="09:00")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sent_key: Mapped[str] = mapped_column(String(30), default="")
