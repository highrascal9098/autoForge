#!/usr/bin/env bash
# autoForge v2 bootstrap — Neon Postgres edition (no local postgres container).
# Prereqs: .env filled, storage_state.json in data/linkedin/, this script run on the VM.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Copy .env.example to .env and fill it in first."; exit 1; }
set -a; . ./.env; set +a

command -v psql >/dev/null || { echo "Installing postgresql-client..."; sudo apt-get update -qq && sudo apt-get install -y -qq postgresql-client; }

echo "Applying schema to Neon..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/schema.sql

echo "Generating n8n credentials from .env..."
python3 - <<'PY' > seed/credentials.json
import json, os
from urllib.parse import urlparse
e = os.environ
u = urlparse(e["DATABASE_URL"])
print(json.dumps([
  {"id": "afPostgres", "name": "AutoForge Neon Postgres", "type": "postgres", "data": {
     "host": u.hostname, "port": u.port or 5432, "database": u.path.lstrip("/"),
     "user": u.username, "password": u.password, "ssl": "require", "maxConnections": 4}},
  {"id": "afSmtp", "name": "AutoForge Gmail SMTP", "type": "smtp", "data": {
     "host": "smtp.gmail.com", "port": 465, "secure": True, "user": e["GMAIL_USER"], "password": e["GMAIL_APP_PASSWORD"]}},
  {"id": "afImap", "name": "AutoForge Gmail IMAP", "type": "imap", "data": {
     "host": "imap.gmail.com", "port": 993, "secure": True, "user": e["GMAIL_USER"], "password": e["GMAIL_APP_PASSWORD"]}},
]))
PY

echo "Starting scraper + n8n..."
docker compose up -d --build scraper

docker compose run --rm --no-deps --entrypoint sh n8n -c \
  "n8n import:credentials --input=/seed/credentials.json && n8n import:workflow --separate --input=/seed/workflows && for id in afErrorNotify1 afDiscovery001 afProcessing01 afOutreach0001 afReplies00001 afFollowups001; do n8n publish:workflow --id=\$id; done"
rm -f seed/credentials.json
docker compose up -d n8n
echo "Done. n8n is on http://localhost:5678 (create the owner account on first visit)."
echo "Tunnel from your PC:  ssh -N -L 5678:127.0.0.1:5678 $(whoami)@$(curl -s ifconfig.me || echo VM_IP)"
