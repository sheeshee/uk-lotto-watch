# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status

Codename "Splendid Tour" — a UK National Lottery watcher. It calls the National Lottery JSON API, stores the latest state, and posts a webhook alert when a watched condition triggers (e.g. Lotto must-be-won, EuroMillions ≥ £100M).

## Project Structure

- `main.py` — orchestrator: fetches games, persists to `games.yml`, evaluates alert conditions, posts to `WEBHOOK`
- `fetch.py` — `AbstractSource` / `NationalLotterySource` (JSON API client), `Fetcher`, and the `Game` dataclass (`next_draw_date`, `jackpot`, `roll_count`)
- `parse.py` — standalone CLI that parses the National Lottery games **HTML** page via BeautifulSoup; no longer used by the main pipeline (kept as a utility for offline HTML)
- `storage.py` — `GamesRepository` persists games to a YAML file
- `tests/` — pytest suite (`test_fetch.py`, `test_parse.py`, `test_storage.py`) plus a fixture HTML file
- `docs/lotto-api.md` — notes on the upstream National Lottery JSON API (the source of truth for endpoint shapes used by `fetch.py`)
- `pyproject.toml` / `uv.lock` — project managed with **uv**

## Dependencies

Python 3.11+. Runtime: `requests`, `dotenv`, `pyyaml`, `beautifulsoup4` (used only by `parse.py`'s HTML CLI). Dev: `pytest`, `pre-commit`, `ruff` (configured via `.pre-commit-config.yaml`).

## Environment

- `WEBHOOK` — required by `main.py` to POST alert messages
- `LOG_LEVEL` — log level for `main.log` (default `WARNING`)

`.env` is loaded via `dotenv`.

## Development Commands

```bash
uv run python main.py        # full pipeline: fetch → store → alert
uv run python fetch.py       # fetch + print parsed games
uv run python parse.py -f tests/national_lottery_games.html
curl … | uv run python parse.py
uv run pytest                # run the test suite
```

## Alerting Logic (`main.py`)

- **Lotto** — alert when `roll_count` crosses from `< 5` to `>= 5` (must-be-won threshold). First-ever run also alerts.
- **EuroMillions** — alert when `jackpot >= £100M` *and* the jackpot value has changed since last seen. This "only notify on change" rule was added deliberately (commit 48b8906) — do not regress to alerting on every run while the threshold is exceeded.

State is read from `games.yml` *before* being overwritten with the new fetch, so the previous-vs-current comparison works on a single run.

## Architecture Notes

- `Fetcher.GAME_IDS` maps watched-game labels to upstream `gameId`s (e.g. `lotto: 1`, `euromillions: 33`). Add a label here to extend coverage.
- `NationalLotterySource` calls two endpoints per game (see `docs/lotto-api.md`):
  - `GET /draw-game/games/{gameId}?deviceType=WEB_CLIENT` → `drawDate` (ISO 8601 UTC) and `topPrize.prizeCents` (pence — divided by 100 to get £)
  - `GET /draw-game/results/{gameId}/latest` → `prizeBreakdown.jackpotRolloverCount` for `roll_count`
  Both calls send `Origin: https://www.national-lottery.co.uk` and require no auth.
- `Fetcher.fetch()` returns `Game | None` per label; downstream (`main.py`) treats `None` as "no data" and skips the alert.
- `parse.py` is independent of the main pipeline — it still reads `<game>-<property>` meta tags from saved HTML and is exercised by `test_parse.py` against `tests/national_lottery_games.html`.
