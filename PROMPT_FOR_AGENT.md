You are working in the `autoforge-n8n` project (already scaffolded; read README.md first).

Goal: get it running end to end on this machine in DRY_RUN mode and fix anything that breaks.

1. Read docker-compose.yml, db/schema.sql, scraper/app.py, scripts/bootstrap.sh and seed/workflows/*.json.
2. Copy .env.example to .env. Ask me for GEMINI_API_KEYS, GMAIL_USER and GMAIL_APP_PASSWORD; keep DRY_RUN=true. Never print secrets or commit .env / storage_state.json.
3. Run ./scripts/bootstrap.sh. If a step fails, fix the root cause (not by disabling checks) and re-run.
4. In n8n, run workflows manually in order: 1 Job discovery, 2 Job processing, 3 Email outreach (draft branch). Verify with psql: rows in jobs, scores set, drafts in outreach, nothing sent.
5. Report: what ran, what failed and how you fixed it, and the SQL showing pipeline counts.

Rules: keep changes minimal and inline (no new abstractions); tests/steps should skip gracefully rather than hard-fail when LinkedIn session or keys are missing; do not set DRY_RUN=false or send any email without my explicit go-ahead; n8n stays the orchestrator, Python only scrapes/extracts.
