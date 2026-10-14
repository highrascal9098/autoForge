-- autoForge v2 schema (Neon Postgres). Run once: psql "$DATABASE_URL" -f db/schema.sql

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    source TEXT DEFAULT 'linkedin',
    post_url TEXT, job_url TEXT, application_url TEXT,
    title TEXT, company TEXT, location TEXT, work_mode TEXT, employment_type TEXT,
    experience_requirement TEXT, salary TEXT, notice_period TEXT,
    description TEXT, full_text TEXT,
    requirements JSONB DEFAULT '[]', skills JSONB DEFAULT '[]', contact_details JSONB DEFAULT '[]',
    author_name TEXT, recruiter_name TEXT, recruiter_profile_url TEXT, recruiter_email TEXT,
    posted_at TEXT, search_keywords TEXT,
    status TEXT DEFAULT 'discovered',          -- discovered, qualified, review, skipped, not_hiring
    match_score INTEGER, match_reasons TEXT,
    scraped_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outreach (
    id SERIAL PRIMARY KEY,
    job_id INTEGER UNIQUE REFERENCES jobs(id),
    recruiter_email TEXT, email_subject TEXT, email_body TEXT,
    status TEXT DEFAULT 'drafted',             -- drafted, sent, replied, pending_user, expired, failed
    sent_at TIMESTAMPTZ, followup_count INTEGER DEFAULT 0, last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    outreach_id INTEGER REFERENCES outreach(id),
    sender_email TEXT, reply_text TEXT,
    sentiment TEXT,                            -- positive, neutral, negative, unsubscribe, interview_request, screening_request, needs_user
    received_at TIMESTAMPTZ DEFAULT now()
);

-- Gemini key round-robin cursor (requirement #14)
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Every-particle logging (requirement #8). Every workflow writes here.
CREATE TABLE IF NOT EXISTS pipeline_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT now(),
    workflow TEXT NOT NULL,
    level TEXT DEFAULT 'info',                 -- info, warn, error
    message TEXT NOT NULL,
    payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_pipeline_log_ts ON pipeline_log(ts DESC);

-- 'Ask me' queue (answer #7): AI unsure -> row here -> dashboard shows it -> you act.
CREATE TABLE IF NOT EXISTS user_alerts (
    id SERIAL PRIMARY KEY,
    outreach_id INTEGER REFERENCES outreach(id),
    kind TEXT,                                 -- needs_user, positive_reply, session_expired
    message TEXT NOT NULL,
    status TEXT DEFAULT 'open',                -- open, resolved
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS system_health (
    task_name TEXT PRIMARY KEY, last_run_at TIMESTAMPTZ DEFAULT now(), status TEXT, details TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
CREATE INDEX IF NOT EXISTS idx_replies_outreach ON replies(outreach_id);

CREATE OR REPLACE VIEW pipeline AS
SELECT (SELECT count(*) FROM jobs WHERE status <> 'not_hiring')      AS discovered,
       (SELECT count(*) FROM jobs WHERE status = 'qualified')        AS qualified,
       (SELECT count(*) FROM outreach WHERE status = 'drafted')      AS drafted,
       (SELECT count(*) FROM outreach WHERE status = 'sent')         AS sent,
       (SELECT count(*) FROM outreach WHERE status = 'replied')      AS replied,
       (SELECT count(*) FROM outreach WHERE status = 'pending_user') AS pending_user,
       (SELECT count(*) FROM outreach WHERE status = 'expired')      AS expired,
       (SELECT count(*) FROM replies)                                AS total_replies;
