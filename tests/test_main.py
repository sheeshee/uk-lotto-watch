import datetime

import pytest

from fetch import Game
from main import alert_for_euromillions, alert_for_lotto

DRAW = datetime.date(2026, 11, 18)


def lotto(roll_count: int) -> Game:
    return Game(next_draw_date=DRAW, jackpot=5_000_000, roll_count=roll_count)


def euromillions(jackpot: int) -> Game:
    return Game(next_draw_date=DRAW, jackpot=jackpot, roll_count=None)


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (None, 1, False),  # first run, below threshold
        (None, 5, True),  # first run, already must-be-won
        (4, 5, True),  # crosses threshold
        (5, 5, False),  # already alerted
        (2, 3, False),
    ],
)
def test_alert_for_lotto(previous, current, expected):
    last_seen = None if previous is None else lotto(previous)
    assert alert_for_lotto(last_seen, lotto(current)) is expected


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (None, 21_000_000, False),  # first run, below threshold
        (None, 150_000_000, True),  # first run, over threshold
        (90_000_000, 110_000_000, True),  # crosses threshold
        (110_000_000, 130_000_000, True),  # changed while over threshold
        (130_000_000, 130_000_000, False),  # unchanged
        (130_000_000, 20_000_000, False),  # won, reset below threshold
    ],
)
def test_alert_for_euromillions(previous, current, expected):
    last_seen = None if previous is None else euromillions(previous)
    assert alert_for_euromillions(last_seen, euromillions(current)) is expected
