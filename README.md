# AutoForge on n8n

Scraper (Playwright + Gemini extraction) runs as a tiny HTTP service; **n8n does all orchestration** on schedules; Postgres is the source of truth.

| Workflow | Schedule (TZ from `.env`) | Does |
|---|---|---|
| 1 Job discovery | every 6h | calls scraper per profile query, saves posts (non-hiring posts remembered so Gemini isn't re-billed) |
| 2 Job processing | every 6h at :30 | Gemini scores `discovered` jobs → `qualified` (>=70) / `review` / `skipped` |
| 3 Email outreach | Mon-Fri 09:30 draft, 10:00 send | drafts with Gemini; sends only if `DRY_RUN=false`, capped by `DAILY_OUTREACH_LIMIT`, 30-90s between mails, 1 mail per recipient per 30 days |
| 4 Reply monitor | IMAP push | classifies replies, marks outreach `replied` (stops follow-ups), emails you on positive/interview replies |
| 5 Follow-ups | Mon-Fri 11:00 | max 2 follow-ups, 2 days apart, only if no reply |
| Error alert | on any failure | emails you (includes expired LinkedIn session) |

## Run
1. `cp .env.example .env` and fill it (Gemini keys, Gmail app password).
2. Put your LinkedIn session at `data/linkedin/storage_state.json` (create with `python scraper/login.py` on a machine with a display).
3. `./scripts/bootstrap.sh` (starts Postgres + scraper, creates n8n credentials, imports + publishes workflows, starts n8n).
4. Open http://localhost:5678 (SSH-tunnel on a server), make the owner account, hit **Manual run** on workflow 1 then 2 then 3 (draft) and inspect `SELECT * FROM outreach;`.
5. When drafts look good: `DRY_RUN=false` in `.env`, `docker compose up -d n8n`.

Edit search queries in `profile/profile.json`. Progress: `SELECT * FROM pipeline;`.

## Changes from the original
- Fixed: post IDs used Python's per-process-randomised `hash()`, so dedup never worked across runs; now sha1-based.
- Fixed: `login.py` saved a browser profile but the scraper read `storage_state.json`.
- SQLite -> Postgres; CLI dashboard, `auto_outreach.py`, `sender.py`, `generator.py` replaced by workflows 3-5.
- Expired LinkedIn session now returns 401 so n8n alerts you instead of silently finding nothing.
- Not ported: Next.js dashboard, tests.
