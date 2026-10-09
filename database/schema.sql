-- Job Outreach System Database Schema

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    source TEXT,
    source_post_id TEXT,
    post_url TEXT,
    job_url TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    work_mode TEXT,
    employment_type TEXT,
    experience_requirement TEXT,
    salary TEXT,
    notice_period TEXT,
    description TEXT,
    full_text TEXT,
    raw_description TEXT,
    requirements TEXT,
    skills TEXT,
    contact_details TEXT,
    recruiter_name TEXT,
    recruiter_profile_url TEXT,
    recruiter_email TEXT,
    application_url TEXT,
    posted_at TEXT,
    search_keywords TEXT,
    status TEXT DEFAULT 'discovered',
    match_score INTEGER,
    match_reasons TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id),
    recruiter_email TEXT,
    email_subject TEXT,
    email_body TEXT,
    status TEXT DEFAULT 'drafted', -- drafted, sent, replied, bounced, needs_review, skipped_duplicate
    sent_at TIMESTAMP,
    followup_count INTEGER DEFAULT 0,
    last_contacted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outreach_id INTEGER REFERENCES outreach(id),
    sender_email TEXT,
    reply_text TEXT,
    sentiment TEXT, -- positive, neutral, negative, unsubscribe, interview_request, screening_request
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outreach_id INTEGER REFERENCES outreach(id),
    job_id INTEGER REFERENCES jobs(id),
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    stage TEXT DEFAULT 'screening', -- screening, technical, final, offer
    interview_date TEXT,
    interview_time TEXT,
    timezone TEXT,
    meeting_url TEXT,
    notes TEXT,
    status TEXT DEFAULT 'scheduled', -- scheduled, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT UNIQUE NOT NULL,
    last_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'success', -- success, error
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_external_id ON jobs(external_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
