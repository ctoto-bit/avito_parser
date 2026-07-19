from aiogram.fsm.state import State, StatesGroup


class SearchForm(StatesGroup):
    waiting_city = State()
    waiting_min_price = State()
    waiting_max_price = State()
    confirming = State()
