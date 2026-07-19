from dataclasses import dataclass

from application.validators import normalize_city


@dataclass(frozen=True, slots=True)
class ResolvedCity:
    name: str
    slug: str


class CityResolver:
    """Нормализует ввод пользователя и строит безопасный адрес поиска Avito."""

    _ALIASES = {
        "мск": "Москва",
        "москва": "Москва",
        "спб": "Санкт-Петербург",
        "питер": "Санкт-Петербург",
        "санкт петербург": "Санкт-Петербург",
        "санкт-петербург": "Санкт-Петербург",
        "нижний новгород": "Нижний Новгород",
    }
    _TRANSLITERATION = str.maketrans(
        {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
            "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
            "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
            "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
            "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
            "э": "e", "ю": "yu", "я": "ya",
        }
    )

    def resolve(self, value: str) -> ResolvedCity:
        city = normalize_city(value)
        canonical_name = self._ALIASES.get(city.casefold(), city)
        slug = self._slugify(canonical_name)
        return ResolvedCity(name=canonical_name, slug=slug)

    @staticmethod
    def _slugify(city: str) -> str:
        value = city.casefold().translate(CityResolver._TRANSLITERATION)
        return "_".join(part for part in value.split() if part)

    def rental_url(self, city: ResolvedCity) -> str:
        return f"https://www.avito.ru/{city.slug}/kvartiry/sdam/na_dlitelnyy_srok"
