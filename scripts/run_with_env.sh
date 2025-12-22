#!/usr/bin/env bash
set -euo pipefail
# Wrapper to load .env and run the CLI in this repo
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo ".env not found in repo root ($ENV_FILE)" >&2
  exit 1
fi

# load .env into the current shell (export all)
set -o allexport
# shellcheck disable=SC1090
source "$ENV_FILE"
set +o allexport

# quick masked sanity check
mask_val() {
  [ -z "${1:-}" ] && echo "<unset>" || echo "<set>"
}
printf "Masked env check:\n"
printf "  AZURE_OPENAI_API_KEY: %s\n" "$(mask_val "$AZURE_OPENAI_API_KEY")"
printf "  AZURE_OPENAI_ENDPOINT: %s\n" "$(mask_val "$AZURE_OPENAI_ENDPOINT")"
printf "  AZURE_OPENAI_CHAT_DEPLOYMENT: %s\n" "$(mask_val "$AZURE_OPENAI_CHAT_DEPLOYMENT")"
printf "  OPENAI_API_KEY: %s\n" "$(mask_val "$OPENAI_API_KEY")"

# run python module with all args
python -m src.rss_job_app.main "$@"
