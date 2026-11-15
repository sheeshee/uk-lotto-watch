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
- `install.sh` — installs a user crontab entry that runs `main.py` (see *Scheduling*)
- `pyproject.toml` / `uv.lock` — project managed with **uv**

## Dependencies

Python 3.11+. Runtime: `requests`, `dotenv`, `pyyaml`, `beautifulsoup4` (used only by `parse.py`'s HTML CLI). Dev group: `pytest`, `pre-commit`. The cron job runs with `--no-dev`, so anything imported by `main.py`/`fetch.py`/`storage.py` must be a runtime dependency.

- `ruff` is not a project dependency; it runs only via the pre-commit hooks (`ruff-check`, `ruff-format`), alongside `uv-lock` and standard whitespace/YAML hooks. Run `uv run pre-commit run --all-files` to lint/format.

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
./install.sh [--dry-run|--uninstall]   # manage the cron job
```

## Scheduling (`install.sh`)

- Adds one crontab line tagged `# uk-lotto-watch`; re-running replaces it, `--uninstall` removes only it. Other crontab entries are preserved.
- The line `cd`s into the repo (state/log files are cwd-relative) and calls uv by absolute path (cron's `PATH` is minimal), appending output to `cron.log`.
- `CRON_SCHEDULE` overrides the default `0 9 * * *`. Alerts only fire on change, so more frequent runs are safe.
- Requires `WEBHOOK` in `.env`. Uses `uv sync --no-dev --inexact` so it doesn't strip dev tools from a shared `.venv`.

## Alerting Logic (`main.py`)

- **Lotto** — alert when `roll_count` crosses from `< 5` to `>= 5` (must-be-won threshold).
- **EuroMillions** — alert when `jackpot >= £100M` *and* the jackpot value has changed since last seen. This "only notify on change" rule was added deliberately (commit 48b8906) — do not regress to alerting on every run while the threshold is exceeded.
- **First run** — if a game has no previous entry in `games.yml`, only the threshold is checked (Lotto `roll_count >= 5`, EuroMillions `jackpot >= £100M`).
- Triggered alerts are joined with newlines and POSTed as a raw UTF-8 body (not JSON).
- Alert rules are covered by `tests/test_main.py`. Importing `main` configures logging to `main.log` in the cwd.

State is read from `games.yml` *before* being overwritten with the new fetch, so the previous-vs-current comparison works on a single run.

## Architecture Notes

- `Fetcher.GAME_SLUGS` maps watched-game labels to upstream `gameSlug`s (`lotto: LOTTO`, `euromillions: EUROMILLIONS`). Add a label here to extend coverage. Do **not** hardcode `gameId`s — they change upstream (Lotto moved 1 → 6 in 2026).
- `NationalLotterySource` first calls `GET /draw-game/games/slugs?deviceType=WEB_CLIENT` once to resolve each slug's `activeGameId`, then two endpoints per game (see `docs/lotto-api.md`):
  - `GET /draw-game/games/{gameId}?deviceType=WEB_CLIENT` → `drawDate` (ISO 8601 UTC) and `topPrize.prizeCents` (pence — divided by 100 to get £)
  - `GET /draw-game/results/{gameId}/latest` → `prizeBreakdown.jackpotRolloverCount` for `roll_count` (`null` for EuroMillions, so `roll_count` is `int | None`)
  Both calls send `Origin: https://www.national-lottery.co.uk` and require no auth.
- `Fetcher.fetch()` catches `KeyError`/`ValueError`/`TypeError`/`requests.RequestException` per game and returns `None` for that label (also for every label if slug resolution fails, or for a slug missing upstream). `main.py` logs and skips `None` games: they are neither stored (so `games.yml` keeps the last good state for the next comparison) nor alerted on.
- `Game.next_draw_date` is a `datetime.date`; `GamesRepository` writes it via `yaml.dump` and reads it back with `yaml.safe_load` (which parses ISO dates back into `date`). `jackpot` is whole pounds.
- `games.yml` and `main.log` are written to the current working directory.
- Tests use fake `AbstractSource` implementations with canned JSON — no network access needed.
- `parse.py` is independent of the main pipeline — it still reads `<game>-<property>` meta tags from saved HTML and is exercised by `test_parse.py` against `tests/national_lottery_games.html`.
