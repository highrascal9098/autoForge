<<<<<<< HEAD
# autoForge — Personal Job Automation System

A lightweight, practical job discovery and outreach automation system built with Python, Playwright, SQLite, n8n, and Google Gemini. Designed to automate job searching, deduplication, AI-powered qualification, and outreach tracking without unnecessary over-architecture or enterprise bloat.

## Architecture

```text
                 JOB SOURCES
                     │
                     ▼
             Python + Playwright
                  SCRAPER
                     │
                     │ JSON
                     ▼
                    n8n
              ORCHESTRATOR
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Database      AI           Gmail
      (SQLite)  Workflows      (OAuth)
        │        (Gemini)         │
        └────────────┤            │
                     ▼            │
              Outreach State      │
                     │            │
                     ▼            │
              Reply Monitoring    │
                     │            │
                     ▼            │
              Follow-up Engine ───┘
                     │
                     ▼
                 Dashboard
```

The system strictly adheres to the principle that **n8n is the primary orchestrator**, while Python is responsible for Playwright browser automation, scraping, extraction, normalization, and returning structured job data. The SQLite database is the single source of truth.

## Project Structure

```text
autoForge/
│
├── scraper/
│   ├── main.py
│   ├── linkedin.py
│   ├── login.py
│   ├── selectors.py
│   ├── posts.py
│   ├── generator.py
│   └── sender.py
│
├── n8n/
│   ├── job-discovery.json
│   ├── job-processing.json
│   ├── email-outreach.json
│   ├── reply-monitor.json
│   └── followups.json
│
├── database/
│   ├── schema.sql
│   └── jobs.db
│
├── profile/
│   profile.json
│
├── tests/
│   └── test_scraper.py
│
├── dashboard.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10+
- n8n (for workflow orchestration)
- Playwright browser binaries (`playwright install chromium`)
- Gemini API key (`GEMINI_API_KEY`) for AI qualification and email generation.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/autoForge.git
cd autoForge
```

2. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your Gemini API key and DB path
```

## Environment Variables

See `.env.example`:

- `GEMINI_API_KEY`: Your Google Gemini API key.
- `AI_MODEL`: LLM model to use (default: `gemini-1.5-flash`).
- `DB_PATH`: Path to SQLite database (default: `database/jobs.db`).
- `LINKEDIN_STORAGE_STATE`: Path to Playwright storage state JSON file (`scraper/storage_state.json`).

## LinkedIn Authentication (Playwright Storage State)

The scraper uses a legitimate authenticated Playwright browser session.

1. Run the interactive login setup tool:

```bash
python -m scraper.login
```

2. Log into LinkedIn manually in the opened browser window. Once your feed loads, close the browser or let it persist.

3. The session state is saved to `scraper/storage_state.json` and reused automatically across all scraping runs. If sessions expire, re-authenticate manually.

## n8n Workflow Orchestration

Import the 5 workflows from `n8n/` into your n8n instance:
- `job-discovery.json`: Triggers Python scraper, normalizes structured job JSON, and saves to SQLite.
- `job-processing.json`: Evaluates jobs against deterministic filters and AI qualification (Gemini strict JSON: `APPLY`, `REVIEW`, `SKIP`).
- `email-outreach.json`: Generates personalized AI outreach emails, enforces safety gates & idempotency, and sends via Gmail OAuth.
- `reply-monitor.json`: Monitors Gmail inbox for replies, classifies sentiment (`INTERESTED`, `NOT_INTERESTED`, etc.), and halts follow-ups upon interest.
- `followups.json`: Executes the strict 2-day follow-up cadence (maximum 2 follow-ups).

## Local CLI Dashboard

Tracks pipeline metrics (Discovered, Qualified, Drafted, Sent, Replies), lists pending outreach drafts, and provides a manual approval & send option.

```bash
python dashboard.py
```

## How to Run Tests

Run pytest to execute unit and database tests:

```bash
pytest
```

## Known Limitations

- **LinkedIn Selectors**: LinkedIn updates DOM classes periodically; selectors in `posts.py` or `selectors.py` may require maintenance.
- **Session Expiry**: LinkedIn session cookies expire over time, requiring re-authentication via `python -m scraper.login`.
- **AI Rate Limits**: Monitor Gemini API quotas when processing large job batches.
=======
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
>>>>>>> origin/n8n
