import pytest

from application.dto import ApartmentCard, SearchRequest
from application.errors import SearchError, StorageError
from application.search_service import SearchService


def apartment(price: int) -> ApartmentCard:
    return ApartmentCard(
        href=f"https://example.test/{price}",
        price=price,
        description="test apartment",
        city="Moscow",
    )


class Gateway:
    def __init__(self, apartments: list[ApartmentCard] | None = None, error: Exception | None = None) -> None:
        self.apartments = apartments or []
        self.error = error

    async def search(self, request: SearchRequest) -> list[ApartmentCard]:
        if self.error is not None:
            raise self.error
        return self.apartments


class Repository:
    def __init__(self, error: Exception | None = None) -> None:
        self.saved: list[ApartmentCard] | None = None
        self.error = error

    async def save_apartments(self, apartments: list[ApartmentCard]) -> None:
        if self.error is not None:
            raise self.error
        self.saved = apartments


@pytest.mark.asyncio
async def test_search_service_filters_results_and_saves_only_matching_apartments() -> None:
    matching = apartment(60_000)
    repository = Repository()
    service = SearchService(
        Gateway([apartment(40_000), matching, apartment(100_000)]),
        repository,
    )
    request = SearchRequest("Moscow", 50_000, 90_000, user_id=1)

    result = await service.search(request)

    assert result.apartments == [matching]
    assert result.total_found == 1
    assert repository.saved == [matching]


@pytest.mark.asyncio
async def test_search_service_wraps_unexpected_gateway_error() -> None:
    service = SearchService(Gateway(error=RuntimeError("network error")), Repository())

    with pytest.raises(SearchError):
        await service.search(SearchRequest("Moscow", 50_000, 90_000, user_id=1))


@pytest.mark.asyncio
async def test_search_service_wraps_unexpected_repository_error() -> None:
    service = SearchService(Gateway([apartment(60_000)]), Repository(error=RuntimeError("disk error")))

    with pytest.raises(StorageError):
        await service.search(SearchRequest("Moscow", 50_000, 90_000, user_id=1))
