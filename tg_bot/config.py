import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Минимальная загрузка .env без дополнительной зависимости."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    database_path: Path
    max_pages: int
    max_results: int
    max_concurrent_searches: int
    rate_limit_seconds: float

    @classmethod
    def from_environment(cls) -> "Config":
        project_root = Path(__file__).resolve().parents[1]
        _load_dotenv(project_root / ".env")
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Не задан BOT_TOKEN. Скопируйте .env.example в .env.")
        return cls(
            bot_token=token,
            database_path=Path(os.getenv("DATABASE_PATH", project_root / "database" / "apartments.db")),
            max_pages=int(os.getenv("MAX_SEARCH_PAGES", "3")),
            max_results=int(os.getenv("MAX_SEARCH_RESULTS", "20")),
            max_concurrent_searches=int(os.getenv("MAX_CONCURRENT_SEARCHES", "1")),
            rate_limit_seconds=float(os.getenv("RATE_LIMIT_SECONDS", "1")),
        )
