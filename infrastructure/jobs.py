import asyncio
import contextlib
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputMediaPhoto

from application.dto import ApartmentCard, SearchRequest, SearchResult
from application.errors import AppError, public_error_message
from application.result_formatter import format_apartment_card, format_search_summary
from application.result_selection import split_initial_apartments
from application.search_service import SearchService
from infrastructure.database.repositories import SqliteApartmentRepository
from tg_bot.keyboards import more_results_keyboard

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchJob:
    chat_id: int
    user_id: int
    request: SearchRequest


@dataclass(slots=True)
class RemainingResults:
    chat_id: int
    apartments: list[ApartmentCard]


class SearchJobQueue:
    """Фоновая очередь поисков с ограничением одновременных браузеров."""

    def __init__(
        self,
        *,
        bot: Bot,
        service: SearchService,
        repository: SqliteApartmentRepository,
        max_concurrent_searches: int = 1,
    ) -> None:
        self._bot = bot
        self._service = service
        self._repository = repository
        self._queue: asyncio.Queue[SearchJob | None] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent_searches)
        self._active_users: set[int] = set()
        self._remaining_results: dict[int, RemainingResults] = {}
        self._remaining_results_lock = asyncio.Lock()
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker(), name="avito-search-worker")

    async def stop(self) -> None:
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._worker_task
        self._worker_task = None

    async def submit(self, job: SearchJob) -> bool:
        if job.user_id in self._active_users:
            return False
        self._active_users.add(job.user_id)
        try:
            await self._queue.put(job)
        except Exception:
            self._active_users.discard(job.user_id)
            raise
        return True

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                return
            try:
                await self._run_job(job)
            finally:
                self._active_users.discard(job.user_id)
                self._queue.task_done()

    async def _run_job(self, job: SearchJob) -> None:
        request = job.request
        job_id: int | None = None
        try:
            job_id = await self._repository.start_search_job(
                user_id=job.user_id,
                city=request.city,
                min_price=request.min_price,
                max_price=request.max_price,
            )
        except AppError as error:
            logger.exception("Не удалось создать запись о поиске для пользователя %s", job.user_id)
            await self._notify_failure(job.chat_id, error)
            return
        except Exception as error:
            logger.exception("Не удалось создать запись о поиске для пользователя %s", job.user_id)
            await self._notify_failure(job.chat_id, error)
            return

        try:
            async with self._semaphore:
                result = await self._service.search(request)
        except AppError as error:
            logger.exception("Поиск для пользователя %s завершился с ошибкой", job.user_id)
            await self._mark_failed(job_id, error)
            await self._notify_failure(job.chat_id, error)
            return
        except Exception as error:
            logger.exception("Неожиданная ошибка поиска для пользователя %s", job.user_id)
            await self._mark_failed(job_id, error)
            await self._notify_failure(job.chat_id, error)
            return

        await self._mark_completed(job_id, result.total_found)
        await self._send_result(job.chat_id, result, user_id=job.user_id)

    async def _mark_completed(self, job_id: int | None, result_count: int) -> None:
        await self._store_job_status(job_id, status="completed", result_count=result_count)

    async def _mark_failed(self, job_id: int | None, error: Exception) -> None:
        await self._store_job_status(
            job_id,
            status="failed",
            result_count=0,
            error=public_error_message(error),
        )

    async def _store_job_status(
        self,
        job_id: int | None,
        *,
        status: str,
        result_count: int = 0,
        error: str | None = None,
    ) -> None:
        if job_id is None:
            return
        try:
            await self._repository.finish_search_job(
                job_id,
                status=status,
                result_count=result_count,
                error=error,
            )
        except AppError:
            logger.exception("Не удалось обновить статус поиска %s", job_id)
        except Exception:
            logger.exception("Не удалось обновить статус поиска %s", job_id)

    async def _notify_failure(self, chat_id: int, error: Exception) -> None:
        try:
            await self._bot.send_message(chat_id, public_error_message(error))
        except TelegramAPIError:
            logger.warning("Не удалось отправить пользователю сообщение об ошибке", exc_info=True)

    async def _send_result(self, chat_id: int, result: SearchResult, *, user_id: int) -> None:
        try:
            await self._bot.send_message(chat_id, format_search_summary(result))
        except TelegramAPIError:
            logger.warning(
                "Не удалось отправить сводку результатов пользователю %s",
                user_id,
                exc_info=True,
            )
            return
        initial_apartments, remaining_apartments = split_initial_apartments(result.apartments)
        async with self._remaining_results_lock:
            self._remaining_results.pop(user_id, None)
            if remaining_apartments:
                self._remaining_results[user_id] = RemainingResults(chat_id, remaining_apartments)

        for apartment in initial_apartments:
            try:
                await self._bot.send_message(chat_id, format_apartment_card(apartment))
            except TelegramAPIError:
                logger.warning(
                    "Не удалось отправить карточку объявления пользователю %s",
                    user_id,
                    exc_info=True,
                )
                continue
            await self._send_images(chat_id, apartment.image_urls)

        if remaining_apartments:
            try:
                await self._bot.send_message(
                    chat_id,
                    "Показаны первые объявления. Нажмите кнопку, чтобы увидеть следующее.",
                    reply_markup=more_results_keyboard,
                )
            except TelegramAPIError:
                logger.warning("Could not send more-results button", exc_info=True)
        elif initial_apartments:
            try:
                await self._bot.send_message(chat_id, "Объявления закончились.")
            except TelegramAPIError:
                logger.warning("Could not send end-of-results message", exc_info=True)

    async def send_next_apartment(self, *, user_id: int, chat_id: int) -> bool | None:
        """Send one remaining result; None means that the button is stale."""
        async with self._remaining_results_lock:
            results = self._remaining_results.get(user_id)
            if results is None or results.chat_id != chat_id:
                return None
            apartment = results.apartments.pop(0)
            has_more = bool(results.apartments)
            if not has_more:
                self._remaining_results.pop(user_id, None)

        try:
            await self._bot.send_message(chat_id, format_apartment_card(apartment))
            await self._send_images(chat_id, apartment.image_urls)
        except TelegramAPIError:
            logger.warning("Could not send apartment card to user %s", user_id, exc_info=True)
        return has_more

    async def _send_images(self, chat_id: int, image_urls: list[str]) -> None:
        urls = image_urls[:3]
        if not urls:
            return
        try:
            if len(urls) == 1:
                await self._bot.send_photo(chat_id, photo=urls[0])
                return
            media = [InputMediaPhoto(media=url) for url in urls]
            await self._bot.send_media_group(chat_id, media=media)
        except TelegramAPIError:
            logger.info("Telegram не смог загрузить фотографии объявления", exc_info=True)
