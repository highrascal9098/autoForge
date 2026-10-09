import os
import sqlite3
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def send_approved_email(to_email, subject, body, resume_path=None):
    """
    Sends an approved email securely using Gmail SMTP and App Passwords.
    Supports optional resume attachment if a valid path is provided.
    Respects dry-run mode and avoids sending without explicit approval.
    """
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if not to_email or "@" not in to_email or "example.com" in to_email:
        logger.warning(f"Invalid or placeholder recipient email: {to_email}")
        return False

    if not gmail_user or not gmail_pass or gmail_user == "your_email@gmail.com":
        logger.warning("Gmail credentials not configured in .env.")
        if dry_run:
            logger.info(f"[DRY RUN] Would send email to {to_email} | Subject: {subject}")
            return True
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Email to {to_email} simulated successfully. Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                attach = MIMEApplication(f.read(), Name=os.path.basename(resume_path))
                attach['Content-Disposition'] = f'attachment; filename="{os.path.basename(resume_path)}"'
                msg.attach(attach)
            logger.info(f"Attached resume: {resume_path}")

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()

        logger.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

class GmailSender:
    def __init__(self, dry_run=None):
        self.dry_run = dry_run

    def send_approved(self, limit=10):
        """
        Sends approved outreach records from the database up to the specified limit.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM outreach
            WHERE status = 'approved'
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} approved outreach record(s) ready to send.")

        sent_count = 0
        for row in rows:
            outreach_id = row["id"]
            job_id = row["job_id"]
            to_email = row["recruiter_email"]
            subject = row["email_subject"]
            body = row["email_body"]

            # Check duplicate send safety
            cursor.execute("SELECT id FROM outreach WHERE job_id = ? AND status = 'sent'", (job_id,))
            if cursor.fetchone():
                logger.warning(f"Duplicate send prevention: Email already sent for job ID {job_id}.")
                cursor.execute("UPDATE outreach SET status = 'skipped_duplicate' WHERE id = ?", (outreach_id,))
                conn.commit()
                continue

            success = send_approved_email(to_email, subject, body)
            if success:
                cursor.execute("""
                    UPDATE outreach
                    SET status = 'sent', sent_at = CURRENT_TIMESTAMP, last_contacted_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (outreach_id,))
                conn.commit()
                sent_count += 1
                logger.info(f"Outreach ID {outreach_id} sent successfully.")
            else:
                cursor.execute("UPDATE outreach SET status = 'failed' WHERE id = ?", (outreach_id,))
                conn.commit()
                logger.warning(f"Outreach ID {outreach_id} sending failed.")

        conn.close()
        return sent_count
