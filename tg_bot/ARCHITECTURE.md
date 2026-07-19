# Архитектура Telegram-бота

## Назначение

Бот принимает от пользователя город, минимальную и максимальную месячную
стоимость аренды квартиры, запускает поиск и показывает подходящие объявления.
Он не должен выполнять браузерный парсер внутри обработчика Telegram: поиск
может занимать минуты и блокировать ответы другим пользователям.

## Слои и зависимости

```text
Telegram
   |
aiogram routers / FSM                 tg_bot/
   |   создаёт SearchRequest
   v
SearchService (сценарий поиска)       application/
   |-- CityResolver                   infrastructure/avito/
   |-- AvitoSearchGateway             infrastructure/avito/
   |-- ApartmentRepository            infrastructure/database/
   `-- ResultFormatter                application/
   v
текущие SearchParser -> Sorter -> Extractor -> Downloader
   v
SQLite: apartments, images, search_jobs
```

Направление импортов — только сверху вниз. `tg_bot` ничего не знает о
Playwright/Camoufox, селекторах Avito или SQL. Парсер не импортирует aiogram.

## Предлагаемая структура

```text
tg_bot/
  __main__.py             # точка запуска polling
  config.py               # BOT_TOKEN, лимиты, путь к БД из окружения
  routers/
    start.py               # /start, /help
    search.py              # FSM и кнопки поиска
    history.py             # /history (опционально)
  states.py                # SearchForm
  keyboards.py             # inline/reply-клавиатуры
  middlewares.py           # логирование, защита от частых запросов

application/
  dto.py                  # SearchRequest, SearchResult, ApartmentCard
  search_service.py       # один сценарий: выполнить поиск и вернуть результат
  validators.py           # валидация города и цен


infrastructure/
  avito/
    city_resolver.py      # город -> slug/URL Avito
    parser_gateway.py     # адаптер к SearchParser, Sorter и Extractor
  database/
    repositories.py       # запросы к Database без aiogram
  jobs.py                 # очередь и worker поисковых задач

parser/                   # существующий низкоуровневый код Playwright
database/                 # существующая схема и подключение SQLite
utils/                    # Apartment, загрузка изображений, нормализация
```

## Диалог с пользователем

Состояния `SearchForm`:

```text
/start
  -> waiting_city
  -> waiting_min_price
  -> waiting_max_price
  -> confirming
  -> поиск поставлен в очередь
  -> результат / ошибка / отмена
```

1. В `waiting_city` бот принимает текст, убирает лишние пробелы и проверяет,
   что город существует через `CityResolver`.
2. В `waiting_min_price` и `waiting_max_price` разрешаются только целые числа
   в рублях: пробелы и `₽` можно игнорировать. Нужны ограничения, например
   от 1 000 до 1 000 000 рублей.
3. После максимальной цены проверяется `min_price <= max_price`; иначе бот
   повторно запрашивает максимум.
4. В `confirming` бот показывает «Город: …, от … до … ₽» и кнопки
   «Искать» / «Изменить» / «Отмена».

Данные FSM хранятся кратковременно (Redis для production, `MemoryStorage` для
локальной разработки). Результаты поиска и история — в SQLite, а не в FSM.

## Контракт сценария поиска

```python
@dataclass(frozen=True)
class SearchRequest:
    city: str
    min_price: int
    max_price: int
    user_id: int

class SearchService:
    async def search(self, request: SearchRequest) -> list[ApartmentCard]: ...
```

`SearchService` формирует URL или применяет выбранный город через
`SearchParser.select_city()`, передаёт границы в парсерный адаптер и возвращает
карточки. Фильтрация цены принадлежит этому сценарию, а не Telegram-роутеру.

## Изменения в существующем коде

Перед подключением бота нужно сделать параметры поиска явными:

- удалить глобальные `URL`, `CITY` и безусловный `asyncio.run(test())` из
  `main.py`; заменить их фабрикой `run_search(request)`;
- изменить `Sorter.sort_by_price()` так, чтобы он получал `min_price` и
  `max_price`, а не использовал `25000` и `35000`;
- передавать город в `SearchParser` и `Extractor` из `SearchRequest` — поле
  `city` уже есть в таблице `apartments`;
- вынести генерацию Avito URL и проверку города в `CityResolver`; не
  конструировать URL из пользовательского текста напрямую;
- сделать `Database` репозиторием: добавить чтение объявлений по `city` и
  диапазону цен, индекс `apartments(city, price)` и при необходимости
  таблицу `search_jobs`.

## Очередь и параллельность

Обработчик «Искать» создаёт задание и сразу отвечает «Ищу объявления…».
Один или несколько worker-ов читают `asyncio.Queue`; количество одновременно
запущенных браузеров ограничивается `asyncio.Semaphore(1)` на старте. После
поиска worker отправляет результат пользователю через `bot.send_message`.
Так один долгий запрос не блокирует polling и не запускает десятки браузеров.

Для перезапуска процесса устойчивую очередь следует хранить в Redis/Celery,
но для первого работающего варианта достаточно `asyncio.Queue`.

## Выдача результата

Каждое объявление отправляется как карточка: цена, краткое описание, город,
ссылка и до трёх фотографий (media group). Сообщения лучше ограничить первыми
10–20 результатами; затем дать кнопку «Показать ещё». Если объявлений нет,
бот сообщает это и предлагает изменить фильтры.

## Конфигурация и безопасность

- `BOT_TOKEN`, путь к БД, лимиты цен и число worker-ов — только через `.env`;
  токен не коммитится.
- На пользователя нужен rate limit и не более одного активного поиска.
- Ошибки Avito/Playwright логируются, пользователю отправляется короткое
  понятное сообщение без traceback.
- Логи не должны содержать токен бота и личные данные пользователя.

## Порядок реализации

1. Выделить `SearchRequest` и параметризовать текущий парсер диапазоном и
   городом.
2. Добавить `SearchService` и проверить его отдельным запуском без Telegram.
3. Создать aiogram-роутер с FSM и валидацией формы.
4. Подключить очередь задач и отправку карточек результатов.
5. Добавить Redis, историю и пагинацию при необходимости.
