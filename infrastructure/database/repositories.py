from application.dto import ApartmentCard, SearchHistoryItem
from database.database_manager import Database


class SqliteApartmentRepository:
    """Адаптер прикладных моделей к существующей SQLite-базе."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def save_apartments(self, apartments: list[ApartmentCard]) -> None:
        for apartment in apartments:
            await self._database.upsert_apartment(
                href=apartment.href,
                price=apartment.price,
                description=apartment.description,
                city=apartment.city,
                image_urls=apartment.image_urls,
            )

    async def start_search_job(self, *, user_id: int, city: str, min_price: int, max_price: int) -> int:
        return await self._database.create_search_job(
            user_id=user_id,
            city=city,
            min_price=min_price,
            max_price=max_price,
        )

    async def finish_search_job(
        self,
        job_id: int,
        *,
        status: str,
        result_count: int = 0,
        error: str | None = None,
    ) -> None:
        await self._database.finish_search_job(
            job_id,
            status=status,
            result_count=result_count,
            error=error,
        )

    async def recent_searches(self, user_id: int, limit: int = 5) -> list[SearchHistoryItem]:
        rows = await self._database.recent_search_jobs(user_id, limit)
        return [
            SearchHistoryItem(
                city=row["city"],
                min_price=row["min_price"],
                max_price=row["max_price"],
                status=row["status"],
                result_count=row["result_count"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
