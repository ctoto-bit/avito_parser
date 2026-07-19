import asyncio


class Sorter:
    """Отбирает ссылки на объявления по переданному диапазону цен."""

    def __init__(
        self,
        queue: asyncio.Queue,
        min_price: int,
        max_price: int,
    ) -> None:
        if min_price > max_price:
            raise ValueError("min_price cannot be greater than max_price")
        self.queue = queue
        self.min_price = min_price
        self.max_price = max_price

    async def sort_by_price(self) -> list[str]:
        result_hrefs: list[str] = []
        while True:
            item = await self.queue.get()
            if item is None:
                break

            hrefs_list, prices_list = item
            for href, price in zip(hrefs_list, prices_list, strict=False):
                if self.min_price <= price <= self.max_price:
                    result_hrefs.append(href)
        return result_hrefs
