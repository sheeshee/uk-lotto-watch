#!/usr/bin/env bash
# Install (or remove) a cron job that runs the full fetch -> store -> notify
# pipeline (main.py) for the current user.
#
# Usage:
#   ./install.sh               install / update the cron job
#   ./install.sh --dry-run     print the cron line without installing
#   ./install.sh --uninstall   remove the cron job
#
# Environment:
#   CRON_SCHEDULE  cron schedule (default: "0 9 * * *", daily at 09:00).
#                  Alerts only fire on change, so running more often is safe.
set -euo pipefail

MARKER="# uk-lotto-watch"
SCHEDULE="${CRON_SCHEDULE:-0 9 * * *}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "error: $*" >&2; exit 1; }

current_crontab() {
    # `crontab -l` exits non-zero when the user has no crontab yet.
    crontab -l 2>/dev/null || true
}

without_our_job() {
    current_crontab | grep -vF "$MARKER" || true
}

mode="install"
case "${1:-}" in
    "") ;;
    --dry-run) mode="dry-run" ;;
    --uninstall) mode="uninstall" ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
esac

command -v crontab >/dev/null || die "crontab not found; install cron first"

if [[ "$mode" == "uninstall" ]]; then
    remaining="$(without_our_job)"
    printf '%s\n' "$remaining" | grep -v '^$' | crontab - || true
    echo "Removed uk-lotto-watch cron job (if it was installed)."
    exit 0
fi

# cron runs with a minimal PATH, so use uv's absolute path.
UV="$(command -v uv)" || die "uv not found on PATH; see https://docs.astral.sh/uv/"

[[ "$REPO_DIR" != *" "* ]] || die "repo path contains spaces, which cron can't handle: $REPO_DIR"

if ! grep -qE '^[[:space:]]*(export[[:space:]]+)?WEBHOOK=.+' "$REPO_DIR/.env" 2>/dev/null; then
    die "WEBHOOK is not set in $REPO_DIR/.env (main.py posts alerts to it).
Create it with:  echo 'WEBHOOK=https://your-webhook-url' >> $REPO_DIR/.env"
fi

# main.py writes games.yml and main.log to its working directory, so cd first.
JOB="$SCHEDULE cd $REPO_DIR && $UV run --no-dev --quiet python main.py >> $REPO_DIR/cron.log 2>&1 $MARKER"

if [[ "$mode" == "dry-run" ]]; then
    echo "$JOB"
    exit 0
fi

echo "Installing runtime dependencies..."
(cd "$REPO_DIR" && "$UV" sync --no-dev --inexact --quiet)

# Read the existing crontab fully before writing it back.
remaining="$(without_our_job)"
{ [[ -n "$remaining" ]] && printf '%s\n' "$remaining"; echo "$JOB"; } | crontab -

echo "Installed cron job:"
echo "  $JOB"
echo "Pipeline log: $REPO_DIR/main.log   cron output: $REPO_DIR/cron.log"
echo "Remove with: $0 --uninstall"
