from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime

import requests


class AbstractSource(ABC):
    @abstractmethod
    def get_upcoming(self, game_id: int) -> dict: ...

    @abstractmethod
    def get_latest_result(self, game_id: int) -> dict: ...


class NationalLotterySource(AbstractSource):
    BASE_URL = "https://api-dfe.national-lottery.co.uk"
    HEADERS = {"Origin": "https://www.national-lottery.co.uk"}

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
    roll_count: int

    def as_dict(self) -> dict:
        return {
            "next_draw_date": self.next_draw_date,
            "jackpot": self.jackpot,
            "roll_count": self.roll_count,
        }


@dataclass
class Fetcher:
    GAME_IDS = {
        "lotto": 1,
        "euromillions": 33,
    }

    source: AbstractSource

    def fetch(self) -> dict[str, Game | None]:
        games: dict[str, Game | None] = {}
        for label, game_id in self.GAME_IDS.items():
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
