import os
import sqlite3
import logging
from datetime import datetime
from outreach.generator import generate_outreach_draft
from outreach.email_sender import GmailSender, send_approved_email
from outreach.tracker import OutreachTracker

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_draft(job_id, recruiter_email, profile=None):
    tracker = OutreachTracker(DB_PATH)
    tracker.init_db()
    if tracker.has_existing_outreach(job_id):
        return False, "Outreach already exists for this job"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()

    if not job:
        return False, "Job not found"

    job_dict = dict(job)
    draft = generate_outreach_draft(job_dict, profile)
    email = recruiter_email or job_dict.get("recruiter_email") or "recruiter@example.com"
    outreach_id = tracker.save_draft(job_id, email, draft)
    if outreach_id:
        return True, "Draft created"
    return False, "Failed to save draft"

def approve_draft(outreach_id):
    tracker = OutreachTracker(DB_PATH)
    tracker.init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE outreach SET status = 'approved' WHERE id = ? AND status IN ('drafted', 'pending_approval')", (outreach_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def send_approved_outreach(outreach_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM outreach WHERE id = ? AND status = 'approved'", (outreach_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "Outreach not found or not approved"

    success = send_approved_email(row["recruiter_email"], row["email_subject"], row["email_body"])
    tracker = OutreachTracker(DB_PATH)
    if success:
        tracker.mark_sent(outreach_id)
        return True, "Sent successfully"
    else:
        tracker.mark_failed(outreach_id)
        return False, "Sending failed"

class OutreachAgent:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.tracker = OutreachTracker(self.db_path)
        self.sender = GmailSender(self.db_path)
        self.tracker.init_db()

    def get_db(self):
        return get_db_connection()

    def create_drafts(self, limit=5):
        """
        Reads discovered jobs without existing outreach and generates personalized drafts.
        """
        conn = self.get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN outreach o ON j.id = o.job_id
            WHERE o.id IS NULL AND (j.status IS NULL OR j.status != 'skipped')
            LIMIT ?
        """, (limit,))
        jobs = cursor.fetchall()
        conn.close()

        drafted_count = 0
        for job in jobs:
            j_dict = dict(job)
            success, _ = create_draft(j_dict['id'], j_dict.get('recruiter_email'))
            if success:
                drafted_count += 1

        logger.info(f"Created {drafted_count} outreach draft(s).")
        return drafted_count

    def approve_draft(self, outreach_id):
        return approve_draft(outreach_id)

    def send_approved(self, limit=5):
        return self.sender.send_approved(limit=limit)
