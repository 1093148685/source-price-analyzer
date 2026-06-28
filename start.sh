#!/usr/bin/env bash
set -euo pipefail
cd /opt/data/apps/source-price-analyzer
export LDXP_USERNAME="hugojin"
if [ -f .env ]; then set -a; source .env; set +a; fi
exec /opt/data/apps/tg-monitor/.venv/bin/python3 app.py
