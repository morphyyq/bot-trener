from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главная", callback_data="home"), InlineKeyboardButton(text="🍔 Питание", callback_data="food")],
            [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="workout"), InlineKeyboardButton(text="😴 Сон", callback_data="sleep")],
            [InlineKeyboardButton(text="💧 Вода", callback_data="water"), InlineKeyboardButton(text="📊 Прогресс", callback_data="progress")],
            [InlineKeyboardButton(text="🤖 AI-тренер", callback_data="trainer"), InlineKeyboardButton(text="🔔 Напоминания", callback_data="reminders")],
            [InlineKeyboardButton(text="⚙️ Профиль", callback_data="profile")],
        ]
    )


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]])


def food_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Фото еды", callback_data="food_photo"), InlineKeyboardButton(text="✍️ Написать еду", callback_data="food_text")],
            [InlineKeyboardButton(text="📊 Сегодня", callback_data="food_today"), InlineKeyboardButton(text="🎯 Моя цель", callback_data="food_goal")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="home")],
        ]
    )


def water_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="+250 мл", callback_data="water_250"), InlineKeyboardButton(text="+500 мл", callback_data="water_500")],
            [InlineKeyboardButton(text="+750 мл", callback_data="water_750"), InlineKeyboardButton(text="Своя сумма", callback_data="water_custom")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="home")],
        ]
    )


def food_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить", callback_data="food_add"), InlineKeyboardButton(text="✏️ Изменить", callback_data="food_edit")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="food_cancel")],
        ]
    )


def clear_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, очистить", callback_data="profile_clear_yes"), InlineKeyboardButton(text="Нет", callback_data="profile_clear_no")]
        ]
    )
