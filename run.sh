#!/usr/bin/env bash
# One-command launcher for Soccer Analytics.
# - installs deps (first run)
# - trains the xG model if it isn't trained yet
# - starts the web app at http://localhost:8000
set -e
cd "$(dirname "$0")"

echo "==> Installing dependencies (first run only)…"
pip install -q -r requirements.txt

if [ ! -f models/xg_model.pkl ]; then
  echo "==> Training the xG model (one-time, ~2-4 min)…"
  python src/xg_model.py
else
  echo "==> xG model already trained — skipping."
fi

echo "==> Starting the web app at http://localhost:8000"
echo "    (Ctrl+C to stop)"
exec uvicorn app:app --host 0.0.0.0 --port 8000
