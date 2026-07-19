import asyncio

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from utils.normalizer import only_digits


class SearchParser:
    """Низкоуровневый сбор ссылок и цен с поисковой выдачи Avito."""

    def __init__(
        self,
        url: str,
        page,
        queue: asyncio.Queue,
        city: str,
        max_pages: int = 3,
    ) -> None:
        self.page = page
        self.city = city
        self.url = url
        self.queue = queue
        self.max_pages = max_pages

    async def next_page(self) -> bool:
        """Переходит на следующую страницу; возвращает True, если страниц больше нет."""
        try:
            await self.page.wait_for_load_state("domcontentloaded")
            locator = self.page.locator('[data-marker="pagination-button/nextPage"]').last
            await expect(locator).to_be_visible(timeout=10_000)
            next_page_url = await locator.get_attribute("href")
            if not next_page_url:
                return True
            url = (
                next_page_url
                if next_page_url.startswith("http")
                else f"https://www.avito.ru{next_page_url}"
            )
            await self.page.goto(url, wait_until="domcontentloaded", timeout=50_000)
            return False
        except PlaywrightTimeoutError:
            return True

    async def entrance(self) -> None:
        await self.page.goto(
            url=self.url,
            wait_until="domcontentloaded",
            timeout=50_000,
        )

    async def collect_apartments_href(self) -> list[str]:
        homes = self.page.locator('[data-marker="item-title"]')
        hrefs: list[str] = []
        for number in range(await homes.count()):
            href = await homes.nth(number).get_attribute("href")
            if href:
                hrefs.append(href if href.startswith("http") else f"https://www.avito.ru{href}")
        return hrefs

    async def collect_apartments_price(self) -> list[int]:
        prices = self.page.locator('[data-marker="item-price-value"]')
        result: list[int] = []
        for number in range(await prices.count()):
            price_text = (await prices.nth(number).all_text_contents())[0]
            result.append(await only_digits(price_text))
        return result

    async def hrefs_and_prices_collector(self) -> None:
        """Кладёт пары списков ``(hrefs, prices)`` в очередь для Sorter."""
        try:
            for page_number in range(self.max_pages):
                await expect(self.page.locator('[data-marker="catalog-serp"]')).to_be_visible(
                    timeout=30_000
                )
                hrefs, prices = await asyncio.gather(
                    self.collect_apartments_href(),
                    self.collect_apartments_price(),
                )
                await self.queue.put((hrefs, prices))
                if page_number + 1 >= self.max_pages or await self.next_page():
                    break
        finally:
            await self.queue.put(None)
