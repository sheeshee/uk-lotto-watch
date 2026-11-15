import os
from dotenv import load_dotenv
import requests
import logging

logger = logging.getLogger(__name__)


load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="main.log",
)


def alert_for_lotto(last_seen_game, current_game) -> bool:
    """Check if Lotto has just become must-be-won (5+ rollovers)."""
    must_be_won = current_game.roll_count >= 5
    if last_seen_game is None:
        # First run: nothing to compare against, so alert on the threshold.
        logger.debug("no previous game for lotto")
        return must_be_won
    trigger_alert = last_seen_game.roll_count < 5 and must_be_won
    logger.debug("trigger lotto alert: %s", trigger_alert)
    return trigger_alert


def alert_for_euromillions(last_seen_game, current_game) -> bool:
    """Check if Euromillions jackpot is over £100 million and has changed."""
    over_threshold = current_game.jackpot >= 100_000_000
    if last_seen_game is None:
        # First run: nothing to compare against, so alert on the threshold.
        logger.debug("no previous game for euromillions")
        return over_threshold
    trigger_alert = over_threshold and last_seen_game.jackpot != current_game.jackpot
    logger.debug("trigger euromillions alert: %s", trigger_alert)
    return trigger_alert


if __name__ == "__main__":
    from fetch import NationalLotterySource, Fetcher
    from storage import GamesRepository

    repo = GamesRepository("games.yml")
    source = NationalLotterySource()
    fetcher = Fetcher(source=source)
    fetched_games = fetcher.fetch()
    logger.debug("fetched: %s", fetched_games)

    previous_games = repo.get_all()
    for label, game in fetched_games.items():
        if game is None:
            # Keep the last good state so the next successful fetch still
            # compares against it.
            logger.warning("no data fetched for %s; skipping", label)
            continue
        repo.add(label, game)

    alerts = []

    # National Lottery
    lotto = fetched_games.get("lotto")
    if lotto is not None and alert_for_lotto(previous_games.get("lotto"), lotto):
        alerts.append(
            f"Lotto must be won! Next draw: {lotto.next_draw_date}, Jackpot: £{lotto.jackpot // 1_000_000}M"
        )

    # Euromillions.
    euromillions = fetched_games.get("euromillions")
    if euromillions is not None and alert_for_euromillions(
        previous_games.get("euromillions"), euromillions
    ):
        alerts.append(
            f"Euromillions jackpot is £{euromillions.jackpot // 1_000_000}M! Next draw: {euromillions.next_draw_date}"
        )

    message = "\n".join(alerts)
    if message:
        logger.debug("posting message: %s", message)
        requests.post(os.environ["WEBHOOK"], data=message.encode(encoding="utf-8"))
    else:
        logger.info("no message to send")
