import os
import sqlite3
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def send_email_via_smtp(to_email, subject, body):
    """
    Sends an email securely using Gmail SMTP and App Passwords.
    """
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

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

def run_sender():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Pull drafted outreach records that have not been sent yet
    cursor.execute("""
        SELECT o.id, o.job_id, o.recruiter_email, o.email_subject, o.email_body, o.status
        FROM outreach o
        WHERE o.status = 'drafted'
    """)
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} drafted outreach emails ready for sending.")

    sent_count = 0
    for row in rows:
        outreach_id = row["id"]
        job_id = row["job_id"]
        to_email = row["recruiter_email"]
        subject = row["email_subject"]
        body = row["email_body"]

        # Safety check: ensure we haven't already sent an email for this job ID
        cursor.execute("SELECT id FROM outreach WHERE job_id = ? AND status = 'sent'", (job_id,))
        existing_sent = cursor.fetchone()
        if existing_sent:
            logger.warning(f"Safety check triggered: Email already sent for job ID {job_id}. Skipping duplicate.")
            cursor.execute("UPDATE outreach SET status = 'skipped_duplicate' WHERE id = ?", (outreach_id,))
            conn.commit()
            continue

        if not to_email or "@" not in to_email or "example.com" in to_email:
            logger.warning(f"Recruiter email invalid or placeholder ({to_email}) for outreach ID {outreach_id}. Flagging for manual review.")
            cursor.execute("UPDATE outreach SET status = 'needs_review' WHERE id = ?", (outreach_id,))
            conn.commit()
            continue

        success = send_email_via_smtp(to_email, subject, body)
        if success:
            cursor.execute("""
                UPDATE outreach
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP, last_contacted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (outreach_id,))
            conn.commit()
            sent_count += 1
            logger.info(f"Outreach ID {outreach_id} marked as 'sent'.")

    conn.close()
    logger.info(f"Sender pipeline completed. Successfully processed and sent {sent_count} emails.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_sender()
