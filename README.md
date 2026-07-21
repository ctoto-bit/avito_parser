# Avito Parser

Telegram-бот и CLI для поиска объявлений об аренде жилья на Avito. Результаты сохраняются в локальную SQLite-базу данных.

## Возможности

- поиск по городу и диапазону цен;
- Telegram-интерфейс с историей запросов;
- запуск поиска из командной строки;
- первые шесть объявлений включают самое дешёвое и самое дорогое из найденных;
- дополнительные объявления выдаются в Telegram по одному, без повторов;
- ограничение параллельных запросов и задержка между действиями;
- хранение результатов в SQLite.

## Требования

- Python 3.11 или новее;
- токен Telegram-бота, полученный у [@BotFather](https://t.me/BotFather).

## Установка

```powershell
git clone https://github.com/ctoto-bit/avito_parser.git
cd avito_parser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m camoufox fetch
```

Команда `python -m camoufox fetch` обязательна: она скачивает браузер Camoufox, который не поставляется вместе с Python-пакетом.

Скопируйте пример настроек и укажите токен:

```powershell
Copy-Item .env.example .env
```

Файл `.env` не должен попадать в Git. База SQLite создаётся автоматически при первом запуске.

Необязательные настройки в `.env`:

```dotenv
DATABASE_PATH=database/apartments.db
MAX_SEARCH_PAGES=3
MAX_SEARCH_RESULTS=20
MAX_CONCURRENT_SEARCHES=1
RATE_LIMIT_SECONDS=1
```

`MAX_SEARCH_RESULTS` задаёт, сколько объявлений парсер получает за один поиск.
Пользователь сначала видит не более шести карточек; оставшиеся доступны по кнопке в боте.

## Запуск

Telegram-бот:

```powershell
python -m tg_bot
```

CLI-поиск:

```powershell
python main.py Москва 50000 90000
```

## Проверка

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Тесты запускаются автоматически в GitHub Actions для каждого push и pull request в ветку `main`.

## Структура

- `application/` — сценарии, DTO и валидация;
- `infrastructure/` — интеграции с Avito, SQLite и очередь задач;
- `tg_bot/` — Telegram-интерфейс;
- `database/` — менеджер SQLite;
- `tests/` — тесты без внешней сети.

## Как устроен поиск

1. Пользователь передаёт город и диапазон цен через Telegram или CLI.
2. Очередь задач запускает один или несколько поисков с заданным лимитом параллельности.
3. Парсер получает объявления, сервис фильтрует и сохраняет их в SQLite.
4. CLI выводит до шести карточек, а бот позволяет последовательно открыть остальные.

## Важное замечание

Проверяйте правила Avito и применимое законодательство перед использованием. Не обходите технические ограничения сервиса и не используйте инструмент для массового сбора данных.

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
