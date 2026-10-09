import os
import sqlite3
import logging
from dotenv import load_dotenv
from scraper.sender import send_email_via_smtp
from scraper.generator import generate_outreach_email, load_profile

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_auto_outreach():
    """
    Automated pipeline:
    1. Fetches scraped posts
    2. Generates AI email
    3. Sends immediately (bypassing approval)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    profile = load_profile()

    # Find posts/jobs to process
    cursor.execute("""
        SELECT j.id, j.title, j.company, j.description, j.url
        FROM jobs j
        LEFT JOIN outreach o ON j.id = o.job_id
        WHERE o.id IS NULL AND j.match_score >= 70
    """)
    rows = cursor.fetchall()

    logger.info(f"Processing {len(rows)} qualified jobs for automatic outreach.")

    for row in rows:
        job_data = {
            "title": row["title"],
            "company": row["company"],
            "description": row["description"],
            "url": row["url"]
        }

        # 1. Generate
        subject, body = generate_outreach_email(job_data, profile)

        # 2. Insert into outreach
        # Assuming recruiter email needs to be handled or placeholder used
        recruiter_email = "recruiter@example.com"

        cursor.execute("""
            INSERT INTO outreach (job_id, recruiter_email, email_subject, email_body, status)
            VALUES (?, ?, ?, ?, 'drafted')
        """, (row["id"], recruiter_email, subject, body))
        outreach_id = cursor.lastrowid

        # 3. Send Immediately
        success = send_email_via_smtp(recruiter_email, subject, body)

        if success:
            cursor.execute("""
                UPDATE outreach
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (outreach_id,))
            logger.info(f"Automatically sent outreach for job {row['id']}")
        else:
            cursor.execute("UPDATE outreach SET status = 'failed' WHERE id = ?", (outreach_id,))
            logger.warning(f"Failed to send outreach for job {row['id']}")

        conn.commit()

    conn.close()
    logger.info("Automatic outreach pipeline complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_auto_outreach()
