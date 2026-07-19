from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from application.dto import SearchRequest
from application.result_formatter import format_price
from application.validators import ValidationError, parse_price, validate_price_range
from infrastructure.avito.city_resolver import CityResolver
from infrastructure.jobs import SearchJob, SearchJobQueue
from tg_bot.keyboards import START_SEARCH_TEXT, confirmation_keyboard
from tg_bot.states import SearchForm


def build_router(city_resolver: CityResolver, jobs: SearchJobQueue) -> Router:
    router = Router(name="search")

    @router.message(Command("search"))
    @router.message(F.text == START_SEARCH_TEXT)
    async def start_search(message: Message, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(SearchForm.waiting_city)
        await message.answer("В каком городе ищем квартиру?")

    @router.message(SearchForm.waiting_city, F.text)
    async def receive_city(message: Message, state: FSMContext) -> None:
        try:
            city = city_resolver.resolve(message.text)
        except ValidationError as error:
            await message.answer(str(error))
            return
        await state.update_data(city=city.name)
        await state.set_state(SearchForm.waiting_min_price)
        await message.answer("Введите минимальную месячную стоимость в рублях.")

    @router.message(SearchForm.waiting_min_price, F.text)
    async def receive_min_price(message: Message, state: FSMContext) -> None:
        try:
            min_price = parse_price(message.text)
        except ValidationError as error:
            await message.answer(str(error))
            return
        await state.update_data(min_price=min_price)
        await state.set_state(SearchForm.waiting_max_price)
        await message.answer("Теперь введите максимальную месячную стоимость в рублях.")

    @router.message(SearchForm.waiting_max_price, F.text)
    async def receive_max_price(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        city = data.get("city")
        min_price = data.get("min_price")
        if city is None or min_price is None:
            await state.clear()
            await message.answer("Сессия поиска устарела. Начните заново через /search.")
            return

        try:
            max_price = parse_price(message.text)
            validate_price_range(min_price, max_price)
        except ValidationError as error:
            await message.answer(str(error))
            return

        await state.update_data(max_price=max_price)
        await state.set_state(SearchForm.confirming)
        await message.answer(
            f"Ищу в городе {city} квартиры от {format_price(min_price)} до {format_price(max_price)}.",
            reply_markup=confirmation_keyboard,
        )

    @router.callback_query(SearchForm.confirming, F.data == "search:confirm")
    async def confirm_search(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        city = data.get("city")
        min_price = data.get("min_price")
        max_price = data.get("max_price")
        if city is None or min_price is None or max_price is None:
            await state.clear()
            await callback.answer()
            if callback.message is not None:
                await callback.message.edit_text("Сессия поиска устарела. Начните заново через /search.")
            return

        request = SearchRequest(
            city=city,
            min_price=min_price,
            max_price=max_price,
            user_id=callback.from_user.id,
        )
        chat_id = callback.message.chat.id if callback.message is not None else callback.from_user.id
        try:
            is_added = await jobs.submit(
                SearchJob(
                    chat_id=chat_id,
                    user_id=callback.from_user.id,
                    request=request,
                )
            )
        except Exception:
            await callback.answer("Не удалось поставить поиск в очередь. Попробуйте позже.", show_alert=True)
            return

        if not is_added:
            await callback.answer("У вас уже есть активный поиск.", show_alert=True)
            return

        await state.clear()
        await callback.answer()
        if callback.message is not None:
            await callback.message.edit_text(
                "Поиск поставлен в очередь. Я пришлю результаты, когда он завершится."
            )

    @router.callback_query(SearchForm.confirming, F.data == "search:edit")
    async def edit_search(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(SearchForm.waiting_city)
        await callback.answer()
        if callback.message is not None:
            await callback.message.edit_text("Введите город заново.")

    @router.callback_query(SearchForm.confirming, F.data == "search:cancel")
    async def cancel_search(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.answer("Поиск отменён")
        if callback.message is not None:
            await callback.message.edit_text("Поиск отменён. Для нового поиска отправьте /search.")

    return router
