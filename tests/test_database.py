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
