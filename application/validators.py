import re

from application.errors import AppError


class ValidationError(AppError, ValueError):
    """Понятная пользователю ошибка ввода."""


MIN_ALLOWED_PRICE = 1_000
MAX_ALLOWED_PRICE = 1_000_000
_CITY_RE = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё -]{1,78}$")
_PRICE_RE = re.compile(r"^[0-9\s₽]+$")


def normalize_city(value: str) -> str:
    city = " ".join(value.strip().split())
    if not _CITY_RE.fullmatch(city):
        raise ValidationError(
            "Введите название города: только буквы, пробелы и дефисы."
        )
    return city


def parse_price(value: str) -> int:
    raw_value = value.strip()
    if not raw_value or not _PRICE_RE.fullmatch(raw_value):
        raise ValidationError("Введите стоимость целым числом в рублях, например: 30 000")

    price = int(re.sub(r"[^0-9]", "", raw_value))
    if not MIN_ALLOWED_PRICE <= price <= MAX_ALLOWED_PRICE:
        raise ValidationError(
            f"Стоимость должна быть от {MIN_ALLOWED_PRICE:,} до {MAX_ALLOWED_PRICE:,} ₽."
            .replace(",", " ")
        )
    return price


def validate_price_range(min_price: int, max_price: int) -> None:
    if min_price > max_price:
        raise ValidationError("Максимальная стоимость не может быть меньше минимальной.")
