#!/usr/bin/env bash
# Deploys the latest main branch: pulls, installs dependencies, and
# restarts the service. Run from the repo root on the production host
# (/srv/shouko-chan/app).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Pulling latest main"
git pull --ff-only origin main

echo "==> Installing dependencies"
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> Restarting service"
sudo systemctl restart shouko-chan.service

echo "==> Done. Tail logs with: journalctl -u shouko-chan -f"
