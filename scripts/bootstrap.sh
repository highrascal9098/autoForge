#!/usr/bin/env bash
# One-time setup: starts the stack, creates n8n credentials from .env, imports + activates the workflows.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Copy .env.example to .env and fill it in first."; exit 1; }
set -a; . ./.env; set +a

python3 - <<'PY' > seed/credentials.json
import json, os
e = os.environ
pw = e["GMAIL_APP_PASSWORD"]
print(json.dumps([
  {"id": "afPostgres", "name": "AutoForge Postgres", "type": "postgres", "data": {
     "host": "postgres", "port": 5432, "database": "autoforge", "user": "autoforge",
     "password": e["POSTGRES_PASSWORD"], "ssl": "disable", "maxConnections": 10}},
  {"id": "afSmtp", "name": "AutoForge Gmail SMTP", "type": "smtp", "data": {
     "host": "smtp.gmail.com", "port": 465, "secure": True, "user": e["GMAIL_USER"], "password": pw}},
  {"id": "afImap", "name": "AutoForge Gmail IMAP", "type": "imap", "data": {
     "host": "imap.gmail.com", "port": 993, "secure": True, "user": e["GMAIL_USER"], "password": pw}},
]))
PY

docker compose up -d --build postgres scraper
docker compose run --rm --no-deps --entrypoint sh n8n -c \
  "n8n import:credentials --input=/seed/credentials.json && n8n import:workflow --separate --input=/seed/workflows && for id in afErrorNotify1 afDiscovery001 afProcessing01 afOutreach0001 afReplies00001 afFollowups001; do n8n publish:workflow --id=\$id; done"
rm -f seed/credentials.json
docker compose up -d n8n
echo "Done. n8n is on http://localhost:5678 (create the owner account on first visit)."
