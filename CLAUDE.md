# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status

Codename "Splendid Tour" — a UK National Lottery watcher. It fetches the National Lottery games page, parses the HTML, stores the latest state, and posts a webhook alert when a watched condition triggers (e.g. Lotto must-be-won, EuroMillions ≥ £100M).

## Project Structure

- `main.py` — orchestrator: fetches games, persists to `games.yml`, evaluates alert conditions, posts to `WEBHOOK`
- `fetch.py` — `AbstractSource` / `NationalLotterySource` (HTTP), `Fetcher`, and the `Game` dataclass (`next_draw_date`, `jackpot`, `roll_count`)
- `parse.py` — `parse_lottery_html()` extracts game info from the page's meta tags via BeautifulSoup; also runnable as a CLI that reads HTML from `-f <file>` or stdin and prints JSON
- `storage.py` — `GamesRepository` persists games to a YAML file
- `tests/` — pytest suite (`test_fetch.py`, `test_parse.py`, `test_storage.py`) plus a fixture HTML file
- `docs/lotto-api.md` — notes on the upstream National Lottery API
- `pyproject.toml` / `uv.lock` — project managed with **uv**

## Dependencies

Python 3.11+. Runtime: `beautifulsoup4`, `requests`, `dotenv`, `pyyaml`. Dev: `pytest`, `pre-commit`, `ruff` (configured via `.pre-commit-config.yaml`).

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

- `Fetcher.WATCHED_GAMES` controls which games are watched; currently `lotto` and `euromillions`.
- `parse.py` reads National Lottery meta tags named `<game>-<property>` (e.g. `lotto-next-draw-jackpot`) — see `game_mappings` and `properties` for the full set. `clean_jackpot()` handles `£`, commas, and `million`/`thousand`/`m`/`k` suffixes.
