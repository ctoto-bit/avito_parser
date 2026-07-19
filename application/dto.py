from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Параметры поиска, собранные ботом для одного пользователя."""

    city: str
    min_price: int
    max_price: int
    user_id: int


@dataclass(slots=True)
class ApartmentCard:
    """Объявление в формате, пригодном для хранения и отправки в Telegram."""

    href: str
    price: int
    description: str
    city: str
    image_urls: list[str] = field(default_factory=list)
    title: str = "Квартира в аренду"


@dataclass(slots=True)
class SearchResult:
    request: SearchRequest
    apartments: list[ApartmentCard]
    total_found: int


@dataclass(frozen=True, slots=True)
class SearchHistoryItem:
    city: str
    min_price: int
    max_price: int
    status: str
    result_count: int
    created_at: str
