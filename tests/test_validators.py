import pytest

from application.validators import ValidationError, normalize_city, parse_price, validate_price_range
from infrastructure.avito.city_resolver import CityResolver


def test_normalize_city_strips_whitespace() -> None:
    assert normalize_city("  Москва  ") == "Москва"


@pytest.mark.parametrize("value", ["", "   ", "Moscow!"])
def test_normalize_city_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_city(value)


@pytest.mark.parametrize(("value", "expected"), [("50 000", 50_000), ("90000", 90_000)])
def test_parse_price(value: str, expected: int) -> None:
    assert parse_price(value) == expected


def test_validate_price_range_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        validate_price_range(90_000, 50_000)


def test_city_resolver_produces_rental_url() -> None:
    city = CityResolver().resolve("Санкт-Петербург")
    assert city.slug == "sankt-peterburg"
    assert CityResolver().rental_url(city).startswith("https://www.avito.ru/")
