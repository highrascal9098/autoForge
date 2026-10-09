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
