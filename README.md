# Avito Parser

Telegram-бот и CLI для поиска объявлений об аренде жилья на Avito. Результаты сохраняются в локальную SQLite-базу данных.

## Возможности

- поиск по городу и диапазону цен;
- Telegram-интерфейс с историей запросов;
- запуск поиска из командной строки;
- ограничение параллельных запросов и задержка между действиями;
- хранение результатов в SQLite.

## Требования

- Python 3.11 или новее;
- токен Telegram-бота, полученный у [@BotFather](https://t.me/BotFather).

## Установка

```powershell
git clone https://github.com/<your-account>/avito-parser.git
cd avito-parser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Скопируйте пример настроек и укажите токен:

```powershell
Copy-Item .env.example .env
```

Файл `.env` не должен попадать в Git. База SQLite создаётся автоматически при первом запуске.

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

## Структура

- `application/` — сценарии, DTO и валидация;
- `infrastructure/` — интеграции с Avito, SQLite и очередь задач;
- `tg_bot/` — Telegram-интерфейс;
- `database/` — менеджер SQLite;
- `tests/` — тесты без внешней сети.

## Важное замечание

Проверяйте правила Avito и применимое законодательство перед использованием. Не обходите технические ограничения сервиса и не используйте инструмент для массового сбора данных.

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
