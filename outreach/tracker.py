import os
import sqlite3
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

class OutreachTracker:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH

    def get_connection(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        schema_path = "database/schema.sql"
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(outreach)")
            cols = [row["name"] for row in cursor.fetchall()]
            new_cols = [
                ("linkedin_message", "TEXT"),
                ("followup_body", "TEXT"),
                ("relevance_explanation", "TEXT"),
                ("provider_message_id", "TEXT"),
                ("resume_path", "TEXT")
            ]
            for col_name, col_type in new_cols:
                if col_name not in cols:
                    cursor.execute(f"ALTER TABLE outreach ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            logger.warning(f"Outreach migration check warning: {e}")

        conn.commit()
        conn.close()

    def has_existing_outreach(self, job_id, recruiter_email=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if recruiter_email:
            cursor.execute("SELECT id FROM outreach WHERE job_id = ? AND recruiter_email = ? AND status != 'skipped_duplicate'", (job_id, recruiter_email))
        else:
            cursor.execute("SELECT id FROM outreach WHERE job_id = ? AND status != 'skipped_duplicate'", (job_id,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def save_draft(self, job_id, recruiter_email, draft_data):
        self.init_db()

        # Validate recipient email (reject placeholders / example.com / empty)
        is_placeholder = not recruiter_email or "@" not in recruiter_email or "example.com" in recruiter_email.lower() or "test.com" in recruiter_email.lower()
        initial_status = 'needs_review' if is_placeholder else 'pending_approval'

        # Check duplicate outreach for same job_id
        if self.has_existing_outreach(job_id):
            logger.warning(f"Duplicate outreach prevention: outreach already exists for job ID {job_id}. Marking as skipped_duplicate.")
            initial_status = 'skipped_duplicate'

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO outreach (
                job_id, recruiter_email, email_subject, email_body,
                linkedin_message, followup_body, relevance_explanation, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            recruiter_email,
            draft_data.get("subject", "Inquiry"),
            draft_data.get("body", ""),
            draft_data.get("linkedin_message", ""),
            draft_data.get("followup_body", ""),
            draft_data.get("relevance_explanation", ""),
            initial_status
        ))
        outreach_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return outreach_id

    def get_pending_approval(self):
        self.init_db()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT o.*, j.company, j.title FROM outreach o JOIN jobs j ON o.job_id = j.id WHERE o.status IN ('pending_approval', 'drafted')")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_approved(self):
        self.init_db()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT o.*, j.company, j.title FROM outreach o JOIN jobs j ON o.job_id = j.id WHERE o.status = 'approved'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self):
        self.init_db()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM outreach GROUP BY status")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_status(self, outreach_id, new_status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE outreach SET status = ? WHERE id = ?", (new_status, outreach_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def approve(self, outreach_id):
        # Send-time / approval-time validation
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM outreach WHERE id = ?", (outreach_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        email = row["recruiter_email"]
        if not email or "@" not in email or "example.com" in email.lower() or "test.com" in email.lower():
            logger.warning(f"Cannot approve outreach ID {outreach_id}: invalid or placeholder recipient email ({email}). Flagging as needs_review.")
            cursor.execute("UPDATE outreach SET status = 'needs_review' WHERE id = ?", (outreach_id,))
            conn.commit()
            conn.close()
            return False

        # Check if another approved/sent outreach exists for this job
        cursor.execute("SELECT id FROM outreach WHERE job_id = ? AND status IN ('approved', 'sent') AND id != ?", (row["job_id"], outreach_id))
        if cursor.fetchone():
            logger.warning(f"Cannot approve outreach ID {outreach_id}: duplicate active outreach for job ID {row['job_id']}. Marking skipped_duplicate.")
            cursor.execute("UPDATE outreach SET status = 'skipped_duplicate' WHERE id = ?", (outreach_id,))
            conn.commit()
            conn.close()
            return False

        cursor.execute("UPDATE outreach SET status = 'approved' WHERE id = ? AND status IN ('drafted', 'pending_approval')", (outreach_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def mark_sent(self, outreach_id, provider_msg_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE outreach
            SET status = 'sent', sent_at = CURRENT_TIMESTAMP, last_contacted_at = CURRENT_TIMESTAMP, provider_message_id = ?
            WHERE id = ?
        """, (provider_msg_id, outreach_id))
        conn.commit()
        conn.close()

    def mark_failed(self, outreach_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE outreach SET status = 'failed' WHERE id = ?", (outreach_id,))
        conn.commit()
        conn.close()
