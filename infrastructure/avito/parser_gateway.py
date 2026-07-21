import asyncio

from camoufox.async_api import AsyncCamoufox

from application.dto import ApartmentCard, SearchRequest
from application.errors import SearchError
from infrastructure.avito.city_resolver import CityResolver
from parser.extractor import Extractor
from parser.search_parser import SearchParser
from utils.sorter import Sorter


class AvitoParserGateway:
    """Адаптирует существующий Playwright-парсер к SearchService."""

    def __init__(
        self,
        city_resolver: CityResolver,
        *,
        max_pages: int = 3,
        max_results: int = 20,
    ) -> None:
        self._city_resolver = city_resolver
        self._max_pages = max_pages
        self._max_results = max_results

    async def search(self, request: SearchRequest) -> list[ApartmentCard]:
        city = self._city_resolver.resolve(request.city)
        url = self._city_resolver.rental_url(city)
        candidate_queue: asyncio.Queue = asyncio.Queue()

        try:
            async with AsyncCamoufox(
                humanize=True,
                window=(1300, 700),
                os="windows",
                enable_cache=True,
                block_images=False,
            ) as browser:
                page = await browser.new_page()
                try:
                    searcher = SearchParser(
                        url=url,
                        page=page,
                        queue=candidate_queue,
                        city=city.name,
                        max_pages=self._max_pages,
                    )
                    sorter = Sorter(
                        queue=candidate_queue,
                        min_price=request.min_price,
                        max_price=request.max_price,
                    )
                    await searcher.entrance()
                    _, hrefs = await asyncio.gather(
                        searcher.hrefs_and_prices_collector(),
                        sorter.sort_by_price(),
                    )

                    extractor = Extractor(
                        hrefs=hrefs,
                        page=page,
                        city=city.name,
                    )
                    apartments = await extractor.collect(limit=self._max_results)
                finally:
                    await page.close()
        except SearchError:
            raise
        except Exception as error:
            raise SearchError("Не удалось получить объявления с Avito. Попробуйте позже.") from error

        return [
            ApartmentCard(
                href=apartment.href,
                price=apartment.price,
                description=apartment.text,
                city=apartment.city,
                image_urls=apartment.images_href,
            )
            for apartment in apartments
        ]
