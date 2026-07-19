"""Независимый от Telegram вход в сценарий поиска."""

import argparse
import asyncio

from application.dto import SearchRequest, SearchResult
from application.result_formatter import format_apartment_card, format_search_summary
from application.result_selection import split_initial_apartments
from application.search_service import SearchService
from database.database_manager import Database
from infrastructure.avito import AvitoParserGateway, CityResolver
from infrastructure.database import SqliteApartmentRepository


def build_search_service(
    gateway: AvitoParserGateway,
    repository: SqliteApartmentRepository,
) -> SearchService:
    return SearchService(gateway=gateway, repository=repository)


async def run_search(
    request: SearchRequest,
    *,
    database_path: str | None = None,
    max_pages: int = 6,
    max_results: int = 20,
) -> SearchResult:
    """Запускает поиск из Python-кода или командной строки без Telegram."""
    database = Database(apartments_db_path=database_path)
    await database.initialize()
    try:
        repository = SqliteApartmentRepository(database)
        city_resolver = CityResolver()
        gateway = AvitoParserGateway(
            city_resolver,
            max_pages=max_pages,
            max_results=max_results,
        )
        service = build_search_service(gateway, repository)
        return await service.search(request)
    finally:
        await database.close()


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Поиск квартир Avito")
    parser.add_argument("city", help="Город поиска")
    parser.add_argument("min_price", type=int, help="Минимальная цена в рублях")
    parser.add_argument("max_price", type=int, help="Максимальная цена в рублях")
    return parser.parse_args()


async def _cli() -> None:
    args = _parse_arguments()
    result = await run_search(
        SearchRequest(
            city=args.city,
            min_price=args.min_price,
            max_price=args.max_price,
            user_id=0,
        )
    )
    print(format_search_summary(result))
    initial_apartments, _ = split_initial_apartments(result.apartments)
    for apartment in initial_apartments:
        print("\n" + format_apartment_card(apartment))


if __name__ == "__main__":
    asyncio.run(_cli())
