from typing import Protocol

from application.dto import ApartmentCard, SearchRequest, SearchResult
from application.errors import AppError, SearchError, StorageError


class ApartmentSearchGateway(Protocol):
    async def search(self, request: SearchRequest) -> list[ApartmentCard]: ...


class ApartmentRepository(Protocol):
    async def save_apartments(self, apartments: list[ApartmentCard]) -> None: ...


class SearchService:
    """Единый сценарий поиска, независимый от Telegram и Playwright."""

    def __init__(
        self,
        gateway: ApartmentSearchGateway,
        repository: ApartmentRepository,
    ) -> None:
        self._gateway = gateway
        self._repository = repository

    async def search(self, request: SearchRequest) -> SearchResult:
        try:
            apartments = await self._gateway.search(request)
        except AppError:
            raise
        except Exception as error:
            raise SearchError() from error

        apartments = [
            apartment
            for apartment in apartments
            if request.min_price <= apartment.price <= request.max_price
        ]
        try:
            await self._repository.save_apartments(apartments)
        except AppError:
            raise
        except Exception as error:
            raise StorageError() from error
        return SearchResult(
            request=request,
            apartments=apartments,
            total_found=len(apartments),
        )
