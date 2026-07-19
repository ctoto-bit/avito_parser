from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

START_SEARCH_TEXT = "🔎 Начать поиск"

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=START_SEARCH_TEXT)]],
    resize_keyboard=True,
)

confirmation_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Искать", callback_data="search:confirm")],
        [InlineKeyboardButton(text="Изменить", callback_data="search:edit")],
        [InlineKeyboardButton(text="Отмена", callback_data="search:cancel")],
    ]
)
