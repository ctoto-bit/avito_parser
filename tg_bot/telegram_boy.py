"""Совместимая точка запуска Telegram-бота.

Предпочтительный запуск: ``python -m tg_bot``.
"""

import asyncio
import logging

from tg_bot.__main__ import main


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
