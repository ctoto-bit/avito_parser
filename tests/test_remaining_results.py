import pytest

from application.dto import ApartmentCard
from infrastructure.jobs import RemainingResults, SearchJobQueue


class BotStub:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> None:
        self.messages.append((chat_id, text))


def apartment(number: int) -> ApartmentCard:
    return ApartmentCard(
        href=f"https://example.test/{number}",
        price=50_000 + number,
        description="test apartment",
        city="Moscow",
    )


@pytest.mark.asyncio
async def test_remaining_results_are_sent_once_and_then_expire() -> None:
    bot = BotStub()
    jobs = SearchJobQueue(bot=bot, service=None, repository=None)
    jobs._remaining_results[7] = RemainingResults(chat_id=11, apartments=[apartment(1), apartment(2)])

    assert await jobs.send_next_apartment(user_id=7, chat_id=11) is True
    assert await jobs.send_next_apartment(user_id=7, chat_id=11) is False
    assert await jobs.send_next_apartment(user_id=7, chat_id=11) is None
    assert [text for _, text in bot.messages] == [
        "Квартира в аренду\n50 001 ₽\ntest apartment\nhttps://example.test/1",
        "Квартира в аренду\n50 002 ₽\ntest apartment\nhttps://example.test/2",
    ]
