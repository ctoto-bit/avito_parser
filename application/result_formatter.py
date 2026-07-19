from application.dto import ApartmentCard, SearchResult


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ") + " ₽"


def format_search_summary(result: SearchResult) -> str:
    request = result.request
    if not result.apartments:
        return (
            f"В городе {request.city} не найдено квартир от "
            f"{format_price(request.min_price)} до {format_price(request.max_price)}."
        )

    return (
        f"Найдено объявлений: {result.total_found}.\n"
        f"{request.city}: от {format_price(request.min_price)} "
        f"до {format_price(request.max_price)}."
    )


def format_apartment_card(card: ApartmentCard) -> str:
    description = " ".join(card.description.split())
    if len(description) > 700:
        description = description[:697].rstrip() + "…"
    return f"{card.title}\n{format_price(card.price)}\n{description}\n{card.href}"
