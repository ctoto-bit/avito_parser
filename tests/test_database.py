from pathlib import Path

import pytest

from database.database_manager import Database


@pytest.mark.asyncio
async def test_database_initializes_and_upserts_apartment(tmp_path: Path) -> None:
    database = Database(apartments_db_path=tmp_path / "apartments.db")
    await database.initialize()
    try:
        apartment_id = await database.upsert_apartment(
            href="https://example.test/apartment/1",
            price=50_000,
            description="Тестовая квартира",
            city="Москва",
            image_urls=["https://example.test/image.jpg"],
        )
        assert apartment_id == 1

        apartment_id = await database.upsert_apartment(
            href="https://example.test/apartment/1",
            price=55_000,
            description="Обновлённая квартира",
            city="Москва",
            image_urls=[],
        )
        assert apartment_id == 1
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_database_stores_and_returns_search_history(tmp_path: Path) -> None:
    database = Database(apartments_db_path=tmp_path / "apartments.db")
    await database.initialize()
    try:
        job_id = await database.create_search_job(
            user_id=42,
            city="Moscow",
            min_price=50_000,
            max_price=90_000,
        )
        await database.finish_search_job(job_id, status="completed", result_count=6)

        history = await database.recent_search_jobs(42)

        assert len(history) == 1
        assert history[0]["city"] == "Moscow"
        assert history[0]["status"] == "completed"
        assert history[0]["result_count"] == 6
    finally:
        await database.close()
