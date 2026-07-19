import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database.database_manager import Database
from infrastructure.avito import AvitoParserGateway, CityResolver
from infrastructure.database import SqliteApartmentRepository
from infrastructure.jobs import SearchJobQueue
from main import build_search_service
from tg_bot.config import Config
from tg_bot.middlewares import RateLimitMiddleware
from tg_bot.routers import history, search, start


async def main() -> None:
    config = Config.from_environment()
    database = Database(apartments_db_path=config.database_path)
    await database.initialize()
    repository = SqliteApartmentRepository(database)
    city_resolver = CityResolver()
    gateway = AvitoParserGateway(
        city_resolver,
        max_pages=config.max_pages,
        max_results=config.max_results,
    )
    service = build_search_service(gateway, repository)
    bot = Bot(token=config.bot_token)
    jobs = SearchJobQueue(
        bot=bot,
        service=service,
        repository=repository,
        max_concurrent_searches=config.max_concurrent_searches,
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    rate_limit = RateLimitMiddleware(config.rate_limit_seconds)
    dispatcher.message.middleware(rate_limit)
    dispatcher.callback_query.middleware(rate_limit)
    dispatcher.include_router(start.build_router())
    dispatcher.include_router(history.build_router(repository))
    dispatcher.include_router(search.build_router(city_resolver, jobs))

    await jobs.start()
    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await jobs.stop()
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
