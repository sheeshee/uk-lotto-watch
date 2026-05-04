from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime

import requests

from parse import parse_lottery_html


class AbstractSource(ABC):
    @abstractmethod
    def get(self) -> str: ...


class NationalLotterySource(AbstractSource):
    URL = "https://www.national-lottery.co.uk/games?icid="

    def get(self) -> str:
        response = requests.get(self.URL)
        return response.text


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
    WATCHED_GAMES = {
        "lotto",
        "euromillions",
    }

    source: AbstractSource

    def fetch(self) -> dict[str, Game]:
        # Simulated fetch logic
        html_content = self.source.get()
        games_data = parse_lottery_html(html_content)
        games = {}
        for game in self.WATCHED_GAMES:
            if game in games_data:
                game_info = games_data[game]
                next_draw_date = game_info.get("next-draw-date")
                jackpot = game_info.get("next-draw-jackpot")
                roll_count = game_info.get("roll-count")
                if next_draw_date and jackpot:
                    games[game] = Game(
                        next_draw_date=next_draw_date,
                        jackpot=jackpot,
                        roll_count=roll_count,
                    )
                else:
                    games[game] = None
            else:
                games[game] = None

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
