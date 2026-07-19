from dataclasses import dataclass, field

@dataclass
class Apartment:
    href: str
    price: int
    text: str
    images_href: list[str]
    city: str = "Не указан"
    images_path: list[str] = field(default_factory=list)
