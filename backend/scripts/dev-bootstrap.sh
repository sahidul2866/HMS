#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$BACKEND_DIR/.venv"
REQUIREMENTS_FILE="$BACKEND_DIR/requirements.txt"
STAMP_FILE="$VENV_DIR/.requirements.sha256"

cd "$BACKEND_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating backend virtualenv..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

CURRENT_REQUIREMENTS_HASH="$(python - <<'PY'
from pathlib import Path
from hashlib import sha256

path = Path("requirements.txt")
print(sha256(path.read_bytes()).hexdigest())
PY
)"

INSTALLED_REQUIREMENTS_HASH=""
if [ -f "$STAMP_FILE" ]; then
  INSTALLED_REQUIREMENTS_HASH="$(cat "$STAMP_FILE")"
fi

if [ "$CURRENT_REQUIREMENTS_HASH" != "$INSTALLED_REQUIREMENTS_HASH" ]; then
  echo "Installing backend requirements..."
  python -m pip install -r "$REQUIREMENTS_FILE"
  printf '%s' "$CURRENT_REQUIREMENTS_HASH" > "$STAMP_FILE"
else
  echo "Backend requirements are up to date."
fi

echo "Running backend migrations and seed scripts..."
PYTHONPATH=. python -m app.scripts.bootstrap_db
echo "Backend bootstrap complete."
