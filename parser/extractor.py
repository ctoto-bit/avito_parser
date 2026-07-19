import asyncio
import logging

from playwright.async_api import expect

from utils.ad_data import Apartment
from utils.normalizer import clean_text

logger = logging.getLogger(__name__)


class Extractor:
    """Извлекает подробности объявления из ссылок, отобранных SearchParser."""

    def __init__(
        self,
        hrefs: list[str],
        page,
        queue: asyncio.Queue | None = None,
        city: str = "Не указан",
    ) -> None:
        self.hrefs = hrefs
        self.page = page
        self.queue = queue
        self.city = city

    async def entrance(self, href: str) -> None:
        await self.page.goto(url=href, wait_until="domcontentloaded", timeout=50_000)

    async def collect_apartment_images_href(self) -> list[str]:
        parents = self.page.locator('[data-marker="image-preview/item"]')
        try:
            await expect(parents.last).to_be_attached(timeout=1_500)
        except Exception:
            return []

        image_urls: list[str] = []
        for number in range(min(3, await parents.count())):
            href = await parents.nth(number).locator("img").get_attribute("src")
            if href:
                image_urls.append(href)
        return image_urls

    async def collect_apartment_price(self) -> int:
        locator = self.page.locator('[data-marker="item-view/item-price"]').last
        await expect(locator).to_be_attached(timeout=3_000)
        content = await locator.get_attribute("content")
        if not content:
            raise ValueError("Не найдена цена объявления")
        return int(content)

    async def collect_apartment_text(self) -> str:
        parents = self.page.locator('[data-marker="item-view/item-params"]')
        await expect(parents.last).to_be_attached(timeout=3_000)

        chunks: list[str] = []
        for number in range(await parents.count()):
            text = (await parents.nth(number).all_text_contents())[0]
            chunks.append(await clean_text(text))
        return "\n".join(chunks)

    async def extract_one(self, href: str) -> Apartment | None:
        try:
            await self.entrance(href)
            price, text, images = await asyncio.gather(
                self.collect_apartment_price(),
                self.collect_apartment_text(),
                self.collect_apartment_images_href(),
                return_exceptions=True,
            )
            required_errors = [item for item in (price, text) if isinstance(item, Exception)]
            if required_errors:
                logger.warning("Пропущено объявление %s: %s", href, required_errors[0])
                return None
            if isinstance(images, Exception):
                images = []
            return Apartment(
                href=href,
                price=price,
                text=text,
                images_href=images,
                city=self.city,
            )
        except Exception:
            logger.exception("Ошибка обработки объявления %s", href)
            return None

    async def collect(self, limit: int | None = None) -> list[Apartment]:
        apartments: list[Apartment] = []
        hrefs = self.hrefs if limit is None else self.hrefs[:limit]
        for href in hrefs:
            apartment = await self.extract_one(href)
            if apartment is not None:
                apartments.append(apartment)
        return apartments

    async def iterator(self) -> None:
        """Обратная совместимость со старым конвейером очередей."""
        if self.queue is None:
            raise RuntimeError("Для iterator требуется очередь")
        try:
            for apartment in await self.collect():
                await self.queue.put(apartment)
        finally:
            await self.queue.put(None)
