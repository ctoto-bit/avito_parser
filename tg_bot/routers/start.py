from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tg_bot.keyboards import main_keyboard


def build_router() -> Router:
    router = Router(name="start")

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Я найду квартиры для долгосрочной аренды на Avito. "
            "Нажмите «Начать поиск» или отправьте /search.",
            reply_markup=main_keyboard,
        )

    return router
