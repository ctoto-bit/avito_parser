"""Select the first page of search results."""

from application.dto import ApartmentCard


INITIAL_RESULTS_LIMIT = 6


def split_initial_apartments(
    apartments: list[ApartmentCard], *, limit: int = INITIAL_RESULTS_LIMIT
) -> tuple[list[ApartmentCard], list[ApartmentCard]]:
    """Split results without duplicates, keeping the cheapest and most expensive first."""
    if limit < 2:
        raise ValueError("limit must be at least 2")
    if len(apartments) <= limit:
        return list(apartments), []

    indexed = list(enumerate(apartments))
    cheapest_index, _ = min(indexed, key=lambda item: item[1].price)
    most_expensive_index, _ = max(indexed, key=lambda item: item[1].price)
    selected_indexes = {cheapest_index, most_expensive_index}
    for index, _ in indexed:
        if len(selected_indexes) == limit:
            break
        selected_indexes.add(index)

    initial = [apartment for index, apartment in indexed if index in selected_indexes]
    remaining = [apartment for index, apartment in indexed if index not in selected_indexes]
    return initial, remaining
