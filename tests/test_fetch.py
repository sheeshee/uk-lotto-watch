import datetime

from fetch import AbstractSource, Fetcher, Game


class FakeSource(AbstractSource):
    def __init__(self, upcoming: dict[int, dict], latest: dict[int, dict]):
        self._upcoming = upcoming
        self._latest = latest

    def get_upcoming(self, game_id: int) -> dict:
        return self._upcoming[game_id]

    def get_latest_result(self, game_id: int) -> dict:
        return self._latest[game_id]


LOTTO_UPCOMING = {
    "gameId": 1,
    "drawDate": "2026-03-07T19:45:00.000Z",
    "topPrize": {"prizeCents": 380_000_000, "nonCashPrize": None},
}
LOTTO_LATEST = {
    "drawResult": {"gameId": 1, "drawNo": 3151},
    "prizeBreakdown": {"jackpotRolloverCount": 0, "isJackpotRollover": False},
}
EUROMILLIONS_UPCOMING = {
    "gameId": 33,
    "drawDate": "2026-03-07T20:45:00.000Z",
    "topPrize": {"prizeCents": 9_600_000_000, "nonCashPrize": None},
}
EUROMILLIONS_LATEST = {
    "drawResult": {"gameId": 33, "drawNo": 1925},
    "prizeBreakdown": {"jackpotRolloverCount": 8, "isJackpotRollover": True},
}


def test_fetch_builds_games_from_api():
    source = FakeSource(
        upcoming={1: LOTTO_UPCOMING, 33: EUROMILLIONS_UPCOMING},
        latest={1: LOTTO_LATEST, 33: EUROMILLIONS_LATEST},
    )
    fetcher = Fetcher(source=source)

    result = fetcher.fetch()

    assert result["lotto"] == Game(
        next_draw_date=datetime.date(2026, 3, 7),
        jackpot=3_800_000,
        roll_count=0,
    )
    assert result["euromillions"] == Game(
        next_draw_date=datetime.date(2026, 3, 7),
        jackpot=96_000_000,
        roll_count=8,
    )
