import asyncio
import contextlib
from pathlib import Path

import aiosqlite

from application.errors import StorageError


class Database:
    """Подключение к SQLite и низкоуровневые запросы приложения."""

    def __init__(
        self,
        db_queue: asyncio.Queue | None = None,
        apartments_db_path: str | Path | None = None,
    ) -> None:
        if apartments_db_path is None:
            apartments_db_path = Path(__file__).parent / "apartments.db"
        self.db_queue = db_queue
        self.apartments_db_path = str(apartments_db_path)
        self.apartments_db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        if self.apartments_db is not None:
            return
        try:
            self.apartments_db = await aiosqlite.connect(self.apartments_db_path)
            self.apartments_db.row_factory = aiosqlite.Row
            await self.apartments_db.execute("PRAGMA foreign_keys = ON")
            await self.apartments_db.execute(
                """
                CREATE TABLE IF NOT EXISTS apartments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    href TEXT UNIQUE NOT NULL,
                    price INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    city TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns_cursor = await self.apartments_db.execute("PRAGMA table_info(apartments)")
            try:
                columns = {row["name"] for row in await columns_cursor.fetchall()}
            finally:
                await columns_cursor.close()
            if "city" not in columns:
                await self.apartments_db.execute(
                    "ALTER TABLE apartments ADD COLUMN city TEXT NOT NULL DEFAULT 'Не указан'"
                )

            await self.apartments_db.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    path TEXT,
                    apartment_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(apartment_id) REFERENCES apartments(id) ON DELETE CASCADE,
                    UNIQUE(url, apartment_id)
                )
                """
            )
            await self.apartments_db.execute(
                "CREATE INDEX IF NOT EXISTS idx_apartments_city_price ON apartments(city, price)"
            )
            await self.apartments_db.execute(
                """
                CREATE TABLE IF NOT EXISTS search_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    city TEXT NOT NULL,
                    min_price INTEGER NOT NULL,
                    max_price INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
                """
            )
            await self.apartments_db.execute(
                "CREATE INDEX IF NOT EXISTS idx_search_jobs_user_created "
                "ON search_jobs(user_id, created_at DESC)"
            )
            await self.apartments_db.commit()
        except aiosqlite.Error as error:
            await self.close()
            raise StorageError("Не удалось инициализировать базу данных.") from error

    def _connection(self) -> aiosqlite.Connection:
        if self.apartments_db is None:
            raise StorageError("Сначала вызовите Database.initialize().")
        return self.apartments_db

    async def upsert_apartment(
        self,
        *,
        href: str,
        price: int,
        description: str,
        city: str,
        image_urls: list[str],
    ) -> int:
        connection = self._connection()
        try:
            await connection.execute(
                """
                INSERT INTO apartments (href, price, description, city)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(href) DO UPDATE SET
                    price = excluded.price,
                    description = excluded.description,
                    city = excluded.city
                """,
                (href, price, description, city),
            )
            cursor = await connection.execute("SELECT id FROM apartments WHERE href = ?", (href,))
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            if row is None:
                raise StorageError("Не удалось сохранить квартиру в базу данных.")
            apartment_id = int(row["id"])
            for url in image_urls:
                await connection.execute(
                    """
                    INSERT INTO images (url, path, apartment_id)
                    SELECT ?, NULL, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM images WHERE url = ? AND apartment_id = ?
                    )
                    """,
                    (url, apartment_id, url, apartment_id),
                )
            await connection.commit()
            return apartment_id
        except StorageError:
            raise
        except aiosqlite.Error as error:
            raise StorageError("Не удалось сохранить квартиру в базу данных.") from error

    async def apartments_save(self, item) -> int:
        """Совместимость с прежним Downloader-конвейером."""
        return await self.upsert_apartment(
            href=item.href,
            price=item.price,
            description=item.text,
            city=item.city,
            image_urls=item.images_href,
        )

    async def images_save(self, item, apartment_id: int) -> None:
        connection = self._connection()
        try:
            for url, path in zip(item.images_href, item.images_path, strict=False):
                cursor = await connection.execute(
                    "UPDATE images SET path = ? WHERE url = ? AND apartment_id = ?",
                    (path, url, apartment_id),
                )
                try:
                    if cursor.rowcount == 0:
                        await connection.execute(
                            "INSERT INTO images (url, path, apartment_id) VALUES (?, ?, ?)",
                            (url, path, apartment_id),
                        )
                finally:
                    await cursor.close()
            await connection.commit()
        except aiosqlite.Error as error:
            raise StorageError("Не удалось сохранить изображения объявления.") from error

    async def save(self) -> None:
        if self.db_queue is None:
            raise StorageError("Для Database.save требуется db_queue.")
        while True:
            item = await self.db_queue.get()
            if item is None:
                return
            apartment_id = await self.apartments_save(item)
            await self.images_save(item, apartment_id)

    async def create_search_job(
        self,
        *,
        user_id: int,
        city: str,
        min_price: int,
        max_price: int,
    ) -> int:
        connection = self._connection()
        try:
            cursor = await connection.execute(
                """
                INSERT INTO search_jobs (user_id, city, min_price, max_price, status)
                VALUES (?, ?, ?, ?, 'running')
                """,
                (user_id, city, min_price, max_price),
            )
            await connection.commit()
            return int(cursor.lastrowid)
        except aiosqlite.Error as error:
            raise StorageError("Не удалось создать запись о поиске.") from error

    async def finish_search_job(
        self,
        job_id: int,
        *,
        status: str,
        result_count: int = 0,
        error: str | None = None,
    ) -> None:
        connection = self._connection()
        try:
            await connection.execute(
                """
                UPDATE search_jobs
                SET status = ?, result_count = ?, error = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, result_count, error, job_id),
            )
            await connection.commit()
        except aiosqlite.Error as error:
            raise StorageError("Не удалось обновить запись о поиске.") from error

    async def recent_search_jobs(self, user_id: int, limit: int = 5) -> list[aiosqlite.Row]:
        connection = self._connection()
        try:
            cursor = await connection.execute(
                """
                SELECT city, min_price, max_price, status, result_count, created_at
                FROM search_jobs WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, limit),
            )
            try:
                rows = await cursor.fetchall()
            finally:
                await cursor.close()
            return rows
        except aiosqlite.Error as error:
            raise StorageError("Не удалось получить историю поисков.") from error

    async def close(self) -> None:
        if self.apartments_db is None:
            return
        connection = self.apartments_db
        self.apartments_db = None
        with contextlib.suppress(Exception):
            await connection.close()

    async def delete_all(self) -> None:
        connection = self._connection()
        try:
            await connection.execute("DELETE FROM apartments")
            await connection.commit()
        except aiosqlite.Error as error:
            raise StorageError("Не удалось очистить таблицу apartments.") from error
