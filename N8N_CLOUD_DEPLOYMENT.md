# AutoForge on n8n Cloud — Zero Local Dependencies Deployment Guide

This guide details how to run **AutoForge** entirely on **n8n Cloud** with **zero local machine dependencies**, running autonomously without needing your local computer or local APIs (`SCRAPER_URL`) running.

---

## Architecture Overview (Cloud-Native)

1. **Job Discovery**: Replaces the local Playwright/Flask scraper with public open job APIs (Remotive API, Arbeitnow API) and Gemini AI discovery directly inside n8n HTTP Request nodes.
2. **Orchestration**: Fully managed by your **n8n Cloud** instance (`*.app.n8n.cloud`).
3. **Database**: Hosted Cloud PostgreSQL (e.g., Supabase, Neon, Render, or Railway) acting as the single source of truth.
4. **AI Processing & Outreach**: Google Gemini API for scoring and email generation + Gmail SMTP/OAuth for sending outreach.

---

## Step 1: Set Up Cloud PostgreSQL
1. Create a free PostgreSQL database on [Supabase](https://supabase.com), [Neon](https://neon.tech), or [Render](https://render.com).
2. Run the SQL schema from `db/schema.sql` in your cloud database SQL editor to create the tables (`jobs`, `outreach`, `replies`, `system_health`) and views.

---

## Step 2: Import Workflows into n8n Cloud
1. Log into your **n8n Cloud account** in Chrome (`https://your-instance.app.n8n.cloud`).
2. Go to **Workflows** -> **Import from File**.
3. Import the workflows provided in the `n8n-cloud/` directory:
   - `01-job-discovery-cloud.json`
   - `02-job-processing-cloud.json`
   - `03-email-outreach-cloud.json`
   - `04-reply-monitor-cloud.json`
   - `05-followups-cloud.json`

---

## Step 3: Configure n8n Credentials & Environment Variables
In your n8n Cloud instance, set up the required credentials:
1. **Postgres Credentials**: Add your cloud PostgreSQL connection details (Host, Database, User, Password, Port 5432). Name the credential `afPostgres`.
2. **Gmail SMTP / IMAP Credentials**: Add your Gmail App Password credentials for outreach and reply monitoring. Name them `afSmtp` and `afImap`.
3. **Environment Variables / Expression Variables**: Ensure your Gemini API keys (`GEMINI_API_KEYS`) and AI model (`AI_MODEL=gemini-2.5-flash` or `gemini-1.5-flash`) are accessible in n8n environment variables or workflow parameters.

---

## Step 4: Activate & Run Autonomously
1. Open each workflow in your n8n Cloud UI and toggle **Active** to **On**.
2. Click **Execute Workflow** (Manual run) on Workflow 1, then Workflow 2, then Workflow 3 to verify the end-to-end pipeline.
3. Everything now runs 100% autonomously on n8n Cloud with zero manual effort or local machine requirements!
