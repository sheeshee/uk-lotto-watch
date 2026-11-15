# Codename: Splendid Tour - A UK National Lottery Webservice

Project Aim: Provide webtools to query and act on the results and draws run by the UK National Lottery.

## Running on a schedule

Requires [uv](https://docs.astral.sh/uv/) and cron.

```bash
echo 'WEBHOOK=https://your-webhook-url' >> .env
./install.sh                                  # daily at 09:00
CRON_SCHEDULE="0 */6 * * *" ./install.sh      # or a custom schedule
./install.sh --dry-run                        # show the cron line only
./install.sh --uninstall                      # remove it
```

Each run fetches the latest Lotto and EuroMillions draw info, saves it to
`games.yml`, and POSTs to `WEBHOOK` when an alert condition is newly met.
Logs go to `main.log` and `cron.log`.
