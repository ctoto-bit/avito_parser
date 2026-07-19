import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from application.errors import AppError, public_error_message
from application.result_formatter import format_price
from infrastructure.database.repositories import SqliteApartmentRepository

logger = logging.getLogger(__name__)


def build_router(repository: SqliteApartmentRepository) -> Router:
    router = Router(name="history")

    @router.message(Command("history"))
    async def history(message: Message) -> None:
        try:
            searches = await repository.recent_searches(message.from_user.id)
        except AppError as error:
            await message.answer(public_error_message(error))
            return
        except Exception:
            logger.exception("Не удалось получить историю поисков для пользователя %s", message.from_user.id)
            await message.answer("Не удалось получить историю поисков. Попробуйте позже.")
            return

        if not searches:
            await message.answer("История поиска пока пуста.")
            return

        lines = ["Последние поиски:"]
        for item in searches:
            lines.append(
                f"• {item.city}: {format_price(item.min_price)}–"
                f"{format_price(item.max_price)}, {item.status}, "
                f"результатов: {item.result_count}"
            )
        await message.answer("\n".join(lines))

    return router
