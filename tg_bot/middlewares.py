import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    """Простой лимит сообщений без внешнего хранилища."""

    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self._last_request: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        now = time.monotonic()
        previous = self._last_request.get(user.id, 0)
        if now - previous < self._seconds:
            if isinstance(event, Message):
                await event.answer("Слишком быстро. Подождите секунду.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Подождите секунду.")
            return None
        self._last_request[user.id] = now
        return await handler(event, data)
