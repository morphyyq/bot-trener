import io
import json
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, func, select

from .ai import AIService, DEFAULT_WORKOUT
from .db import SessionLocal, get_or_create_daily, get_profile, nutrition_totals
from .keyboards import back_menu, clear_confirm, food_confirm, food_menu, main_menu, water_menu
from .models import BodyWeight, DailyStat, FoodEntry, Reminder, UserProfile, WorkoutSession
from .utils import fmt_number, parse_hhmm, safe_float, safe_int, sleep_duration_minutes

router = Router()
ai_service = AIService()


class Onboarding(StatesGroup):
    name = State()
    age = State()
    gender = State()
    height = State()
    weight = State()
    goal = State()
    activity = State()
    workouts = State()
    sleep = State()
    wake = State()
    equipment = State()


class FoodInput(StatesGroup):
    text = State()
    photo = State()
    edit = State()


class WaterInput(StatesGroup):
    amount = State()


class SleepInput(StatesGroup):
    times = State()


class ReminderInput(StatesGroup):
    time = State()


async def profile_dict(profile: UserProfile) -> dict:
    return {
        "name": profile.name,
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "workouts_per_week": profile.workouts_per_week,
        "sleep_time": profile.sleep_time,
        "wake_time": profile.wake_time,
        "equipment": profile.equipment,
    }


async def show_home(message: Message, telegram_id: int) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, telegram_id)
        if not profile:
            await message.answer("Профиль ещё не создан. Нажмите /start.")
            return
        today = date.today()
        daily = await get_or_create_daily(session, telegram_id, today)
        totals = await nutrition_totals(session, telegram_id, today)
        await session.commit()
        goal = profile.goal or "не указана"
        workout = "✅" if daily.workout_done else "⬜"
        sleep = f"{daily.sleep_minutes // 60} ч {daily.sleep_minutes % 60:02d} мин" if daily.sleep_minutes else "не записан"
        text = (
            f"🏠 <b>Главная</b>\n\n"
            f"👤 {profile.name}\n⚖️ Вес: {fmt_number(profile.weight_kg or 0)} кг\n📏 Рост: {fmt_number(profile.height_cm or 0)} см\n🎯 Цель: {goal}\n\n"
            f"<b>Сегодня:</b>\n"
            f"🏋️ Тренировка: {workout}\n"
            f"🍔 Питание: {fmt_number(totals['calories'])} ккал, Б {fmt_number(totals['protein'])} / Ж {fmt_number(totals['fat'])} / У {fmt_number(totals['carbs'])} г\n"
            f"💧 Вода: {daily.water_ml} мл\n"
            f"😴 Сон: {sleep}\n"
            f"🔥 XP: {daily.xp}"
        )
        await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, message.from_user.id)
    if profile:
        await show_home(message, message.from_user.id)
        return
    await state.set_state(Onboarding.name)
    await message.answer("Привет! Я помогу вести тренировки, питание, воду, сон и прогресс. Это не медицинский сервис.\n\nКак тебя называть?")


@router.message(Onboarding.name)
async def onboarding_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(Onboarding.age)
    await message.answer("Сколько тебе лет? Напиши целое число.")


@router.message(Onboarding.age)
async def onboarding_age(message: Message, state: FSMContext) -> None:
    age = safe_int(message.text)
    if age is None or not 5 <= age <= 120:
        await message.answer("Введи возраст числом, например 25.")
        return
    await state.update_data(age=age)
    await state.set_state(Onboarding.gender)
    await message.answer("Укажи пол или напиши «не хочу указывать».")


@router.message(Onboarding.gender)
async def onboarding_gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=message.text.strip())
    await state.set_state(Onboarding.height)
    await message.answer("Рост в сантиметрах? Например: 178")


@router.message(Onboarding.height)
async def onboarding_height(message: Message, state: FSMContext) -> None:
    height = safe_float(message.text)
    if height is None or not 80 <= height <= 250:
        await message.answer("Введи рост числом от 80 до 250 см.")
        return
    await state.update_data(height_cm=height)
    await state.set_state(Onboarding.weight)
    await message.answer("Вес в килограммах? Например: 72.5")


@router.message(Onboarding.weight)
async def onboarding_weight(message: Message, state: FSMContext) -> None:
    weight = safe_float(message.text)
    if weight is None or not 20 <= weight <= 400:
        await message.answer("Введи вес числом от 20 до 400 кг.")
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(Onboarding.goal)
    await message.answer("Цель: набрать мышечную массу, поддерживать форму, похудеть или стать сильнее?")


@router.message(Onboarding.goal)
async def onboarding_goal(message: Message, state: FSMContext) -> None:
    await state.update_data(goal=message.text.strip())
    await state.set_state(Onboarding.activity)
    await message.answer("Какой у тебя уровень активности? Например: низкий, средний, высокий.")


@router.message(Onboarding.activity)
async def onboarding_activity(message: Message, state: FSMContext) -> None:
    await state.update_data(activity_level=message.text.strip())
    await state.set_state(Onboarding.workouts)
    await message.answer("Сколько тренировок в неделю планируешь? Например: 3")


@router.message(Onboarding.workouts)
async def onboarding_workouts(message: Message, state: FSMContext) -> None:
    workouts = safe_int(message.text)
    if workouts is None or not 0 <= workouts <= 14:
        await message.answer("Введи число от 0 до 14.")
        return
    await state.update_data(workouts_per_week=workouts)
    await state.set_state(Onboarding.sleep)
    await message.answer("Во сколько обычно ложишься? Формат ЧЧ:ММ, например 23:30")


@router.message(Onboarding.sleep)
async def onboarding_sleep(message: Message, state: FSMContext) -> None:
    value = parse_hhmm(message.text)
    if not value:
        await message.answer("Нужен формат ЧЧ:ММ, например 23:30")
        return
    await state.update_data(sleep_time=value)
    await state.set_state(Onboarding.wake)
    await message.answer("Во сколько обычно просыпаешься? Формат ЧЧ:ММ")


@router.message(Onboarding.wake)
async def onboarding_wake(message: Message, state: FSMContext) -> None:
    value = parse_hhmm(message.text)
    if not value:
        await message.answer("Нужен формат ЧЧ:ММ, например 07:30")
        return
    await state.update_data(wake_time=value)
    await state.set_state(Onboarding.equipment)
    await message.answer("Есть ли доступ к оборудованию? Например: нет, турник, гантели 2x10 кг, зал.")


@router.message(Onboarding.equipment)
async def onboarding_equipment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    data["equipment"] = message.text.strip()
    async with SessionLocal() as session:
        profile = UserProfile(telegram_id=message.from_user.id, **data)
        session.add(profile)
        await session.flush()
        plan = await ai_service.generate_plan(await profile_dict(profile))
        profile.plan_json = json.dumps(plan, ensure_ascii=False)
        session.add(BodyWeight(telegram_id=message.from_user.id, weight_kg=profile.weight_kg or 0))
        await session.commit()
    await state.clear()
    await message.answer("✅ Профиль сохранён. Создаю персональный план...")
    summary = "AI подключён" if ai_service.client else "Сейчас использую базовый безопасный план, а после добавления ключа DeepSeek включится AI-анализ"
    await message.answer(f"🎯 План готов. {summary}.\n\nВыбирай нужный раздел:", reply_markup=main_menu())


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery) -> None:
    await callback.answer()
    await show_home(callback.message, callback.from_user.id)


@router.callback_query(F.data == "food")
async def cb_food(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("🍔 <b>ПИТАНИЕ</b>\n\nМожно добавить еду текстом или фотографией. Оценка калорий и БЖУ приблизительная.", reply_markup=food_menu(), parse_mode="HTML")


@router.callback_query(F.data == "food_text")
async def cb_food_text(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FoodInput.text)
    await callback.message.answer("Напиши, что и примерно сколько ты съел. Например: «2 яйца, бутерброд с сыром и банан».")


@router.message(FoodInput.text)
async def food_text_received(message: Message, state: FSMContext) -> None:
    result = await ai_service.analyze_food_text(message.text)
    await state.update_data(pending_food=result)
    await message.answer(food_preview(result), reply_markup=food_confirm())


@router.callback_query(F.data == "food_photo")
async def cb_food_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FoodInput.photo)
    await callback.message.answer("Отправь фотографию еды одним сообщением. Оценка по фото будет приблизительной.")


@router.message(FoodInput.photo, F.photo)
async def food_photo_received(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await message.bot.download(file, destination=buffer)
    result = await ai_service.analyze_food_image(buffer.getvalue(), "image/jpeg")
    await state.update_data(pending_food=result)
    await message.answer(food_preview(result), reply_markup=food_confirm())


def food_preview(result: dict) -> str:
    return (
        f"🍽 <b>Предположительно:</b> {result['description']}\n\n"
        f"🔥 ~{fmt_number(result['calories'])} ккал\n"
        f"🥩 Белки: ~{fmt_number(result['protein'])} г\n"
        f"🍞 Углеводы: ~{fmt_number(result['carbs'])} г\n"
        f"🥑 Жиры: ~{fmt_number(result['fat'])} г\n\n"
        f"⚠️ Оценка приблизительная, особенно при анализе фотографии."
    )


@router.callback_query(F.data == "food_add")
async def cb_food_add(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    result = data.get("pending_food")
    if not result:
        await callback.answer("Нет данных для добавления", show_alert=True)
        return
    async with SessionLocal() as session:
        session.add(FoodEntry(telegram_id=callback.from_user.id, description=result["description"], calories=result["calories"], protein_g=result["protein"], fat_g=result["fat"], carbs_g=result["carbs"], source="photo" if data.get("photo") else "text"))
        await session.commit()
    await state.clear()
    await callback.answer("Добавлено")
    await callback.message.answer("✅ Записал в питание за сегодня.", reply_markup=food_menu())


@router.callback_query(F.data == "food_edit")
async def cb_food_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FoodInput.edit)
    await callback.message.answer("Напиши уточнение, например: «это была большая порция, примерно 250 г».")


@router.message(FoodInput.edit)
async def food_edit_received(message: Message, state: FSMContext) -> None:
    result = await ai_service.analyze_food_text(message.text)
    await state.update_data(pending_food=result)
    await message.answer(food_preview(result), reply_markup=food_confirm())


@router.callback_query(F.data == "food_cancel")
async def cb_food_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.answer("Запись отменена.", reply_markup=food_menu())


@router.callback_query(F.data == "food_today")
async def cb_food_today(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        totals = await nutrition_totals(session, callback.from_user.id, date.today())
        result = await session.execute(select(FoodEntry).where(FoodEntry.telegram_id == callback.from_user.id, func.date(FoodEntry.eaten_at) == date.today()).order_by(FoodEntry.eaten_at))
        entries = result.scalars().all()
    lines = [f"🍔 <b>Сегодня</b>\n🔥 Калории: {fmt_number(totals['calories'])}\n🥩 Белки: {fmt_number(totals['protein'])} г\n🍞 Углеводы: {fmt_number(totals['carbs'])} г\n🥑 Жиры: {fmt_number(totals['fat'])} г\n"]
    if entries:
        lines.append("<b>Съедено:</b>")
        lines.extend([f"• {entry.description} · {fmt_number(entry.calories)} ккал" for entry in entries])
    else:
        lines.append("Пока ничего не записано.")
    await callback.answer()
    await callback.message.answer("\n".join(lines), reply_markup=food_menu(), parse_mode="HTML")


@router.callback_query(F.data == "food_goal")
async def cb_food_goal(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, callback.from_user.id)
        plan = json.loads(profile.plan_json or "{}") if profile else {}
    await callback.answer()
    await callback.message.answer(f"🎯 <b>Ориентир по питанию</b>\n\n{plan.get('nutrition', 'План пока не создан.')}\n\nКалории и БЖУ не являются медицинской нормой.", reply_markup=food_menu(), parse_mode="HTML")


@router.callback_query(F.data == "water")
async def cb_water(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        daily = await get_or_create_daily(session, callback.from_user.id, date.today())
        await session.commit()
    await callback.answer()
    await callback.message.answer(f"💧 <b>ВОДА</b>\n\nСегодня: {daily.water_ml} мл / ориентир 2000 мл\n\nНажми кнопку для быстрого добавления.", reply_markup=water_menu(), parse_mode="HTML")


@router.callback_query(F.data.startswith("water_"))
async def cb_water_add(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split("_")[1]
    if value == "custom":
        await callback.answer()
        await state.set_state(WaterInput.amount)
        await callback.message.answer("Сколько миллилитров добавить? Например: 350")
        return
    amount = int(value)
    async with SessionLocal() as session:
        daily = await get_or_create_daily(session, callback.from_user.id, date.today())
        daily.water_ml += amount
        await session.commit()
        total = daily.water_ml
    await callback.answer(f"+{amount} мл")
    await callback.message.answer(f"💧 Сегодня: {total} мл", reply_markup=water_menu())


@router.message(WaterInput.amount)
async def water_custom_received(message: Message, state: FSMContext) -> None:
    amount = safe_int(message.text)
    if amount is None or amount <= 0 or amount > 5000:
        await message.answer("Введи количество от 1 до 5000 мл.")
        return
    async with SessionLocal() as session:
        daily = await get_or_create_daily(session, message.from_user.id, date.today())
        daily.water_ml += amount
        await session.commit()
        total = daily.water_ml
    await state.clear()
    await message.answer(f"💧 Добавлено {amount} мл. Сегодня: {total} мл", reply_markup=water_menu())


@router.callback_query(F.data == "sleep")
async def cb_sleep(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SleepInput.times)
    await callback.message.answer("Напиши время сна и пробуждения через пробел. Например: 23:30 08:00")


@router.message(SleepInput.times)
async def sleep_received(message: Message, state: FSMContext) -> None:
    parts = message.text.split()
    if len(parts) != 2 or not parse_hhmm(parts[0]) or not parse_hhmm(parts[1]):
        await message.answer("Формат: 23:30 08:00")
        return
    minutes = sleep_duration_minutes(parts[0], parts[1])
    async with SessionLocal() as session:
        daily = await get_or_create_daily(session, message.from_user.id, date.today())
        daily.sleep_minutes = minutes
        await session.commit()
    await state.clear()
    quality = "✅ Хорошее восстановление" if minutes >= 8 * 60 else "⚠️ Возможно, сна маловато"
    await message.answer(f"😴 Сон: {minutes // 60} ч {minutes % 60:02d} мин\n{quality}\n\nДля подростков ориентир часто составляет около 8–10 часов, но это не медицинская норма.", reply_markup=main_menu())


async def today_workout(profile: UserProfile) -> dict:
    try:
        plan = json.loads(profile.plan_json or "{}")
        workouts = plan.get("workouts") or [DEFAULT_WORKOUT]
        return workouts[date.today().weekday() % len(workouts)]
    except Exception:
        return DEFAULT_WORKOUT


@router.callback_query(F.data == "workout")
async def cb_workout(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, callback.from_user.id)
    workout = await today_workout(profile)
    lines = [f"🏋️ <b>{workout.get('name', 'Тренировка')}</b>\n\nСегодняшний план:"]
    buttons = []
    for index, exercise in enumerate(workout.get("exercises", [])):
        lines.append(f"{index + 1}. {exercise.get('name', 'Упражнение')} — {exercise.get('sets', 3)} подхода × {exercise.get('reps', 'по плану')}")
        buttons.append([InlineKeyboardButton(text=f"▶️ Начать: {exercise.get('name', 'упражнение')}", callback_data=f"exercise_start:{index}")])
    buttons.append([InlineKeyboardButton(text="✅ Завершить тренировку", callback_data="workout_done")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="home")])
    await callback.answer()
    await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


async def get_or_create_session(session, user_id: int, workout: dict) -> WorkoutSession:
    result = await session.execute(select(WorkoutSession).where(WorkoutSession.telegram_id == user_id, WorkoutSession.session_date == date.today(), WorkoutSession.completed.is_(False)).order_by(WorkoutSession.id.desc()))
    current = result.scalars().first()
    if current:
        return current
    payload = [{**exercise, "done": False} for exercise in workout.get("exercises", [])]
    current = WorkoutSession(telegram_id=user_id, session_date=date.today(), name=workout.get("name", "Тренировка"), exercises_json=json.dumps(payload, ensure_ascii=False))
    session.add(current)
    await session.flush()
    return current


@router.callback_query(F.data.startswith("exercise_start:"))
async def cb_exercise_start(callback: CallbackQuery) -> None:
    index = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        profile = await get_profile(session, callback.from_user.id)
        workout = await today_workout(profile)
        current = await get_or_create_session(session, callback.from_user.id, workout)
        exercises = json.loads(current.exercises_json)
        if 0 <= index < len(exercises):
            exercises[index]["done"] = True
            current.exercises_json = json.dumps(exercises, ensure_ascii=False)
        await session.commit()
    await callback.answer("Упражнение отмечено")
    await callback.message.answer(f"✅ Выполнено: {workout['exercises'][index].get('name', 'упражнение')}\nНе спеши и сохраняй технику.")


@router.callback_query(F.data == "workout_done")
async def cb_workout_done(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, callback.from_user.id)
        workout = await today_workout(profile)
        current = await get_or_create_session(session, callback.from_user.id, workout)
        current.completed = True
        current.completed_at = datetime.utcnow()
        current.duration_seconds = max(0, int((current.completed_at - current.started_at).total_seconds()))
        daily = await get_or_create_daily(session, callback.from_user.id, date.today())
        daily.workout_done = True
        daily.xp += 20
        await session.commit()
    await callback.answer("Тренировка сохранена")
    await callback.message.answer("🎉 <b>Тренировка завершена!</b>\n\nЯ сохранил дату, упражнения и время. В следующей версии AI будет подробнее учитывать лёгкость выполнения и постепенно менять нагрузку.", reply_markup=main_menu(), parse_mode="HTML")


REMINDER_LABELS = {"workout": "🏋️ Тренировки", "food": "🍔 Питание", "water": "💧 Вода", "sleep": "😴 Сон"}


@router.callback_query(F.data == "reminders")
async def cb_reminders(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(Reminder).where(Reminder.telegram_id == callback.from_user.id).order_by(Reminder.kind))
        reminders = {item.kind: item for item in result.scalars().all()}
        for kind, default_time in [("workout", "18:00"), ("food", "13:30"), ("water", "11:00"), ("sleep", "22:30")]:
            if kind not in reminders:
                item = Reminder(telegram_id=callback.from_user.id, kind=kind, reminder_time=default_time, enabled=True)
                session.add(item)
                reminders[kind] = item
        await session.commit()
    lines = ["🔔 <b>Напоминания</b>", "Нажми, чтобы включить/выключить. Время можно изменить отдельной кнопкой."]
    buttons = []
    for kind in ("workout", "food", "water", "sleep"):
        item = reminders[kind]
        status = "✅" if item.enabled else "⬜"
        lines.append(f"{status} {REMINDER_LABELS[kind]} — {item.reminder_time}")
        buttons.append([InlineKeyboardButton(text=f"{status} {REMINDER_LABELS[kind]}", callback_data=f"rem_toggle:{kind}"), InlineKeyboardButton(text="Изменить время", callback_data=f"rem_time:{kind}")])
    buttons.append([InlineKeyboardButton(text="🏠 Назад", callback_data="home")])
    await callback.answer()
    await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.callback_query(F.data.startswith("rem_toggle:"))
async def cb_rem_toggle(callback: CallbackQuery) -> None:
    kind = callback.data.split(":")[1]
    async with SessionLocal() as session:
        result = await session.execute(select(Reminder).where(Reminder.telegram_id == callback.from_user.id, Reminder.kind == kind))
        item = result.scalar_one_or_none()
        if item:
            item.enabled = not item.enabled
            await session.commit()
    await callback.answer("Настройка изменена")
    await cb_reminders(callback)


@router.callback_query(F.data.startswith("rem_time:"))
async def cb_rem_time(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data.split(":")[1]
    await state.update_data(reminder_kind=kind)
    await state.set_state(ReminderInput.time)
    await callback.answer()
    await callback.message.answer(f"Напиши новое время для раздела «{REMINDER_LABELS.get(kind, kind)}» в формате ЧЧ:ММ")


@router.message(ReminderInput.time)
async def reminder_time_received(message: Message, state: FSMContext) -> None:
    value = parse_hhmm(message.text)
    if not value:
        await message.answer("Формат должен быть ЧЧ:ММ, например 18:00")
        return
    data = await state.get_data()
    async with SessionLocal() as session:
        result = await session.execute(select(Reminder).where(Reminder.telegram_id == message.from_user.id, Reminder.kind == data["reminder_kind"]))
        item = result.scalar_one_or_none()
        if item:
            item.reminder_time = value
        else:
            session.add(Reminder(telegram_id=message.from_user.id, kind=data["reminder_kind"], reminder_time=value, enabled=True))
        await session.commit()
    await state.clear()
    await message.answer("✅ Время сохранено.", reply_markup=main_menu())


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, callback.from_user.id)
    if not profile:
        await callback.answer("Сначала создай профиль через /start", show_alert=True)
        return
    text = (f"⚙️ <b>ПРОФИЛЬ</b>\n\n👤 Имя: {profile.name}\n🎂 Возраст: {profile.age}\n📏 Рост: {profile.height_cm} см\n⚖️ Вес: {profile.weight_kg} кг\n🎯 Цель: {profile.goal}\n🏃 Активность: {profile.activity_level}\n🏋️ Оборудование: {profile.equipment}\n😴 Сон: {profile.sleep_time}–{profile.wake_time}\n🏋️ Тренировок в неделю: {profile.workouts_per_week}")
    buttons = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✏️ Изменить данные", callback_data="profile_edit")], [InlineKeyboardButton(text="🔔 Напоминания", callback_data="reminders")], [InlineKeyboardButton(text="🗑 Очистить данные", callback_data="profile_clear")], [InlineKeyboardButton(text="🏠 Назад", callback_data="home")]])
    await callback.answer()
    await callback.message.answer(text, reply_markup=buttons, parse_mode="HTML")


@router.callback_query(F.data == "profile_clear")
async def cb_profile_clear(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Удалить профиль, питание, тренировки, воду, сон и прогресс? Это действие нельзя отменить.", reply_markup=clear_confirm())


@router.callback_query(F.data == "profile_clear_no")
async def cb_profile_clear_no(callback: CallbackQuery) -> None:
    await callback.answer("Отменено")
    await callback.message.answer("Данные оставлены.", reply_markup=main_menu())


@router.callback_query(F.data == "profile_clear_yes")
async def cb_profile_clear_yes(callback: CallbackQuery, state: FSMContext) -> None:
    async with SessionLocal() as session:
        for model in (FoodEntry, DailyStat, WorkoutSession, BodyWeight, Reminder, UserProfile):
            await session.execute(delete(model).where(model.telegram_id == callback.from_user.id))
        await session.commit()
    await state.clear()
    await callback.answer("Удалено")
    await callback.message.answer("Данные удалены. Для нового профиля нажми /start.")


@router.callback_query(F.data == "profile_edit")
async def cb_profile_edit(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Для простоты первой версии используй /start после очистки данных. В следующем шаге добавим редактирование отдельных полей без удаления профиля.")


@router.callback_query(F.data == "progress")
async def cb_progress(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        weights = (await session.execute(select(BodyWeight).where(BodyWeight.telegram_id == callback.from_user.id).order_by(BodyWeight.measured_at))).scalars().all()
        workouts = (await session.execute(select(func.count(WorkoutSession.id)).where(WorkoutSession.telegram_id == callback.from_user.id, WorkoutSession.completed.is_(True)))).scalar() or 0
        avg_sleep = (await session.execute(select(func.avg(DailyStat.sleep_minutes)).where(DailyStat.telegram_id == callback.from_user.id, DailyStat.sleep_minutes > 0))).scalar()
    if weights:
        change = weights[-1].weight_kg - weights[0].weight_kg
        weight_text = f"{weights[0].weight_kg:.1f} → {weights[-1].weight_kg:.1f} кг ({change:+.1f} кг)"
    else:
        weight_text = "нет данных"
    sleep_text = f"{float(avg_sleep) / 60:.1f} ч" if avg_sleep else "нет данных"
    text = f"📊 <b>ПРОГРЕСС</b>\n\n⚖️ Изменение веса: {weight_text}\n🏋️ Завершённых тренировок: {workouts}\n😴 Средний сон: {sleep_text}\n💪 Подтягивания и отжимания: появятся после добавления тестов/подходов в журнал упражнений."
    await callback.answer()
    await callback.message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "trainer")
async def cb_trainer(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("🤖 Напиши обычным сообщением, что тебя интересует. Например: «Я плохо спал, стоит ли сегодня тренироваться?»", reply_markup=main_menu())


@router.message(F.text)
async def free_text(message: Message) -> None:
    async with SessionLocal() as session:
        profile = await get_profile(session, message.from_user.id)
        if not profile:
            await message.answer("Чтобы начать, нажми /start.")
            return
        totals = await nutrition_totals(session, message.from_user.id, date.today())
        daily = await get_or_create_daily(session, message.from_user.id, date.today())
        result = await session.execute(select(WorkoutSession).where(WorkoutSession.telegram_id == message.from_user.id).order_by(WorkoutSession.session_date.desc()).limit(5))
        workouts = result.scalars().all()
        context = f"Сегодня питание: {totals}; вода: {daily.water_ml} мл; сон: {daily.sleep_minutes} минут; последних тренировок: {len(workouts)}"
        profile_data = await profile_dict(profile)
        await session.commit()
    answer = await ai_service.trainer_answer(profile_data, context, message.text)
    await message.answer(answer, reply_markup=main_menu())
