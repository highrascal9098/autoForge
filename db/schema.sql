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
    status TEXT DEFAULT 'drafted',             -- drafted, sent, replied, failed
    sent_at TIMESTAMPTZ, followup_count INTEGER DEFAULT 0, last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    outreach_id INTEGER REFERENCES outreach(id),
    sender_email TEXT, reply_text TEXT,
    sentiment TEXT,                            -- positive, neutral, negative, unsubscribe, interview_request, screening_request
    received_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_health (
    task_name TEXT PRIMARY KEY, last_run_at TIMESTAMPTZ DEFAULT now(), status TEXT, details TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);

CREATE OR REPLACE VIEW pipeline AS
SELECT (SELECT count(*) FROM jobs WHERE status <> 'not_hiring')      AS discovered,
       (SELECT count(*) FROM jobs WHERE status = 'qualified')        AS qualified,
       (SELECT count(*) FROM outreach WHERE status = 'drafted')      AS drafted,
       (SELECT count(*) FROM outreach WHERE sent_at IS NOT NULL)     AS sent,
       (SELECT count(*) FROM replies)                                AS replies;
