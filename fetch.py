from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime

import requests


class AbstractSource(ABC):
    @abstractmethod
    def get_game_slugs(self) -> dict: ...

    @abstractmethod
    def get_upcoming(self, game_id: int) -> dict: ...

    @abstractmethod
    def get_latest_result(self, game_id: int) -> dict: ...


class NationalLotterySource(AbstractSource):
    BASE_URL = "https://api-dfe.national-lottery.co.uk"
    HEADERS = {"Origin": "https://www.national-lottery.co.uk"}

    def get_game_slugs(self) -> dict:
        response = requests.get(
            f"{self.BASE_URL}/draw-game/games/slugs",
            params={"deviceType": "WEB_CLIENT"},
            headers=self.HEADERS,
        )
        response.raise_for_status()
        return response.json()

    def get_upcoming(self, game_id: int) -> dict:
        response = requests.get(
            f"{self.BASE_URL}/draw-game/games/{game_id}",
            params={"deviceType": "WEB_CLIENT"},
            headers=self.HEADERS,
        )
        response.raise_for_status()
        return response.json()

    def get_latest_result(self, game_id: int) -> dict:
        response = requests.get(
            f"{self.BASE_URL}/draw-game/results/{game_id}/latest",
            headers=self.HEADERS,
        )
        response.raise_for_status()
        return response.json()


@dataclass
class Game:
    next_draw_date: datetime.date
    jackpot: int
    roll_count: int | None  # EuroMillions results report no rollover count

    def as_dict(self) -> dict:
        return {
            "next_draw_date": self.next_draw_date,
            "jackpot": self.jackpot,
            "roll_count": self.roll_count,
        }


@dataclass
class Fetcher:
    # Watched-game label -> upstream gameSlug. Active gameIds change over
    # time (e.g. Lotto moved from 1 to 6), so they are resolved per fetch.
    GAME_SLUGS = {
        "lotto": "LOTTO",
        "euromillions": "EUROMILLIONS",
    }

    source: AbstractSource

    def resolve_game_ids(self) -> dict[str, int]:
        slugs = self.source.get_game_slugs()["gameSlugs"]
        active = {entry["gameSlug"]: entry["activeGameId"] for entry in slugs}
        return {
            label: active[slug]
            for label, slug in self.GAME_SLUGS.items()
            if slug in active
        }

    def fetch(self) -> dict[str, Game | None]:
        games: dict[str, Game | None] = {label: None for label in self.GAME_SLUGS}
        try:
            game_ids = self.resolve_game_ids()
        except (KeyError, TypeError, requests.RequestException):
            return games
        for label, game_id in game_ids.items():
            try:
                upcoming = self.source.get_upcoming(game_id)
                latest = self.source.get_latest_result(game_id)
                games[label] = Game(
                    next_draw_date=datetime.datetime.fromisoformat(
                        upcoming["drawDate"].replace("Z", "+00:00")
                    ).date(),
                    jackpot=upcoming["topPrize"]["prizeCents"] // 100,
                    roll_count=latest["prizeBreakdown"]["jackpotRolloverCount"],
                )
            except (KeyError, ValueError, TypeError, requests.RequestException):
                games[label] = None
        return games


if __name__ == "__main__":
    source = NationalLotterySource()
    fetcher = Fetcher(source=source)
    games = fetcher.fetch()
    for game_name, game in games.items():
        if game:
            print(
                f"{game_name.capitalize()}: Next draw on {game.next_draw_date}, Jackpot: £{game.jackpot:,d}, Roll count: {game.roll_count}"
            )
        else:
            print(f"{game_name.capitalize()}: No data available.")
