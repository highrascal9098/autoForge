# autoForge — Project Audit Report

## Working
- **Playwright Authentication & Login**: `scraper/login.py` successfully launches persistent context (`scraper/browser_profile`) for manual login and state persistence.
- **LinkedIn Post Scraping**: `scraper/posts.py` scrapes LinkedIn search results dynamically with multi-selector fallbacks and scrolling.
- **Database Schema**: `database/schema.sql` defines structured SQLite tables (`jobs`, `outreach`, `replies`) with indexes and foreign keys.
- **CLI Dashboard**: `dashboard.py` displays pipeline metrics, pending outreach drafts, and provides manual approval & send functionality.
- **Unit Tests**: `tests/test_scraper.py` successfully runs and passes deduplication and database initialization tests.
- **Gemini Key Rotation**: `scraper/ai_client.py` supports multi-key rotation and retry logic for Google Gemini API calls.

## Partially Working
- **Python Scraper & Pipeline (`scraper/main.py`)**: Successfully scrapes and evaluates jobs, but conflates scraping with orchestration (performing AI evaluation and database insertion directly in Python rather than returning structured JSON for n8n orchestration).
- **n8n Workflows (`n8n/*.json`)**: Workflow definitions exist and are importable, but contain architectural mismatches (using `n8n-nodes-base.postgres` for an SQLite database, missing actual AI nodes, missing Gmail OAuth integration, missing idempotency checks, and incomplete reply monitoring/follow-up logic).
- **Email Outreach (`scraper/generator.py`, `scraper/sender.py`, `scraper/auto_outreach.py`)**: Functional SMTP sender and Gemini generator, but duplicates responsibilities that belong in n8n according to the intended architecture.

## Broken
- **Database Connectivity in n8n**: The n8n workflows (`job-processing.json`, `email-outreach.json`, `followups.json`) attempt to use PostgreSQL nodes (`n8n-nodes-base.postgres`) against the SQLite file database (`database/jobs.db`), which will fail execution.
- **End-to-End Orchestration**: Autonomous execution relies on Python scripts executing directly rather than n8n acting as the central orchestrator coordinating scraping, qualification, generation, sending, and follow-ups.

## Missing
- **n8n SQLite / HTTP Integration**: n8n workflows lack nodes to query/write to the SQLite database or execute the Python scraper via structured HTTP/CLI output.
- **n8n AI Nodes**: n8n workflows lack AI nodes / HTTP nodes for job qualification and email generation using Gemini.
- **n8n Gmail OAuth Integration**: n8n workflows currently use basic text/email placeholders or missing credential mappings instead of native Gmail OAuth integration.
- **Deterministic Email Safety Gates & Idempotency in n8n**: Guardrails (already implemented in Python `sender.py`) need to be reflected in n8n workflow logic to prevent duplicate sends and enforce strict limits.

## Architecture Problems
- **Inverted Orchestrator Responsibility**: The original implementation had Python running the end-to-end pipeline (`main.py`, `auto_outreach.py`), treating n8n as a superficial wrapper (`executeCommand`) rather than n8n being the primary orchestrator.
- **Database Source of Truth Mismatch**: n8n workflows referenced PostgreSQL instead of SQLite.
- **Logic Duplication**: Email generation and sending logic existed both in Python (`generator.py`, `sender.py`) and n8n specifications, violating the single source of truth principle.

## Security Problems
- **SMTP Password in Environment**: README and initial setup suggested `GMAIL_APP_PASSWORD` and SMTP instead of n8n Gmail OAuth credentials.
- **Anti-bot Bypass Misrepresentation**: README previously referenced bypassing LinkedIn anti-bot protection; this must be corrected to legitimate authenticated browser sessions using Playwright storage state.

## Duplicate Logic
- AI qualification and email generation logic duplicated across Python modules and n8n workflow expectations.
- Email sending implemented in both `scraper/sender.py`, `scraper/auto_outreach.py`, and n8n `email-outreach.json`.

## Recommended Fixes
1. **Refocus Python on Scraping & Extraction**: Make Python scripts (`scraper/main.py` or a clean scraper runner) output structured JSON matching the required schema (source, source_post_id, url, company, job_title, location, description, requirements, skills, recruiter details, posted_at).
2. **Correct n8n Workflows**: Update all 5 n8n workflows (`job-discovery.json`, `job-processing.json`, `email-outreach.json`, `reply-monitor.json`, `followups.json`) to use SQLite/Execute Command / HTTP nodes properly, integrating AI evaluation, deterministic filtering, Gmail OAuth, idempotency checks, reply classification, and follow-up cadences.
3. **Consolidate Orchestration**: Establish n8n as the primary workflow orchestrator and database as the source of truth, while preserving reusable Python modules for robust Playwright scraping.
4. **Update README**: Rewrite `README.md` to accurately reflect the correct architecture, Playwright storage state usage, n8n setup, and removal of anti-bot bypass terminology.

## Priority Order
1. Rewrite `README.md` and document the corrected architecture.
2. Refine Python scraper (`scraper/main.py`, `scraper/posts.py`) to output clean structured JSON for n8n ingestion.
3. Update n8n workflow JSONs to use correct SQLite/Execute nodes, AI nodes, and Gmail OAuth integration.
4. Validate tests and verify end-to-end pipeline components.
