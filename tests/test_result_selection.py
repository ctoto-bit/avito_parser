from application.dto import ApartmentCard
from application.result_selection import split_initial_apartments


def apartment(price: int) -> ApartmentCard:
    return ApartmentCard(
        href=f"https://example.test/{price}",
        price=price,
        description="test",
        city="Moscow",
    )


def test_returns_all_results_when_fewer_than_six_are_found() -> None:
    apartments = [apartment(price) for price in (40_000, 50_000, 60_000)]

    initial, remaining = split_initial_apartments(apartments)

    assert initial == apartments
    assert remaining == []


def test_first_six_contain_cheapest_and_most_expensive_without_duplicates() -> None:
    apartments = [apartment(price) for price in (50_000, 90_000, 40_000, 80_000, 70_000, 60_000, 100_000, 30_000)]

    initial, remaining = split_initial_apartments(apartments)

    assert len(initial) == 6
    assert min(card.price for card in initial) == 30_000
    assert max(card.price for card in initial) == 100_000
    assert len({card.href for card in initial + remaining}) == len(apartments)
    assert {card.href for card in initial + remaining} == {card.href for card in apartments}
