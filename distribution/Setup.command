#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
RESOURCES="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-${GOOGLEBOOK_WORK:-$HOME/.local/share/try-googlebook-os/work}}"
if ! command -v uv >/dev/null; then
  printf 'Install Homebrew and uv first: https://brew.sh\nThen run: brew install uv\n'
  exit 1
fi
exec uv run --no-project --python 3.12 "$RESOURCES/source/distribution/setup.py" "$RESOURCES/source" "$WORK"
