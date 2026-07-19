import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from application.errors import public_error_message

logger = logging.getLogger(__name__)


def build_router() -> Router:
    router = Router(name="errors")

    @router.errors()
    async def handle_error(event: ErrorEvent) -> bool:
        exception = event.exception
        logger.error(
            "Unhandled error while processing update %s",
            getattr(event.update, "update_id", None),
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        await _notify_user(event, public_error_message(exception))
        return True

    return router


async def _notify_user(event: ErrorEvent, message: str) -> None:
    update = event.update
    try:
        if update.callback_query is not None:
            await update.callback_query.answer(message, show_alert=True)
            return
        if update.message is not None:
            await update.message.answer(message)
    except TelegramAPIError:
        logger.warning("Не удалось показать пользователю сообщение об ошибке", exc_info=True)
