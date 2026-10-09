import os
import sqlite3
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from scraper.main import run_scraper_to_json
from outreach.agent import OutreachAgent
from outreach.tracker import OutreachTracker

load_dotenv()
app = Flask(__name__)
API_KEY = os.getenv("AUTOFORGE_API_KEY")
DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

scraper_lock = threading.Lock()
is_scraping_active = False

def require_api_key(f):
    def decorated_function(*args, **kwargs):
        if not API_KEY or API_KEY == "your_secret_key" or request.headers.get("X-API-KEY") != API_KEY:
            return jsonify({"error": "Unauthorized / Invalid API Key"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def is_valid_email(email):
    if not email or "@" not in email:
        return False
    lower = email.lower()
    for domain in ["example.com", "example.org", "example.net", "test.com", "placeholder.com"]:
        if domain in lower:
            return False
    return True

@app.route("/api/trigger-scrape", methods=["POST"])
@require_api_key
def trigger_scrape():
    global is_scraping_active
    with scraper_lock:
        if is_scraping_active:
            return jsonify({"status": "running", "message": "Scraper is already running."}), 429

    def run():
        global is_scraping_active
        with scraper_lock:
            is_scraping_active = True
        try:
            run_scraper_to_json()
        except Exception as e:
            app.logger.error(f"Scraper error: {e}")
        finally:
            with scraper_lock:
                is_scraping_active = False

    threading.Thread(target=run).start()
    return jsonify({"status": "started", "message": "Scraper triggered successfully."}), 202

@app.route("/api/scrape/status", methods=["GET"])
@require_api_key
def scrape_status():
    return jsonify({"is_scraping_active": is_scraping_active})

@app.route("/api/jobs/new", methods=["GET"])
@require_api_key
def get_new_jobs():
    limit = request.args.get("limit", 10, type=int)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs
        WHERE status = 'discovered'
        AND id NOT IN (SELECT job_id FROM outreach)
        LIMIT ?
    """, (limit,))
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route("/api/outreach/draft", methods=["POST"])
@require_api_key
def create_outreach_draft():
    data = request.json or {}
    job_id = data.get("job_id")
    recruiter_email = data.get("recruiter_email")

    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    if not is_valid_email(recruiter_email):
        return jsonify({"error": "Invalid or placeholder recipient email"}), 400

    agent = OutreachAgent(DB_PATH)
    if agent.tracker.has_existing_outreach(job_id, recruiter_email):
        return jsonify({"error": "Duplicate outreach for this job and recipient"}), 409

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()

    if not job:
        return jsonify({"error": "Job not found"}), 404

    from outreach.generator import generate_outreach_draft
    draft = generate_outreach_draft(dict(job))
    outreach_id = agent.tracker.save_draft(job_id, recruiter_email, draft)
    return jsonify({"status": "success", "outreach_id": outreach_id})

@app.route("/api/outreach/pending", methods=["GET"])
@require_api_key
def get_pending_outreach():
    tracker = OutreachTracker(DB_PATH)
    return jsonify(tracker.get_pending_approval())

@app.route("/api/outreach/approved", methods=["GET"])
@require_api_key
def get_approved_outreach():
    tracker = OutreachTracker(DB_PATH)
    return jsonify(tracker.get_approved())

@app.route("/api/outreach/active", methods=["GET"])
@require_api_key
def get_active_outreach():
    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT o.*, j.company, j.title FROM outreach o JOIN jobs j ON o.job_id = j.id WHERE o.status IN ('sent', 'approved')")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/outreach/record-sent", methods=["POST"])
@require_api_key
def record_sent():
    data = request.json or {}
    outreach_id = data.get("outreach_id")
    provider_id = data.get("provider_message_id")
    idempotency_key = data.get("idempotency_key")

    if not outreach_id:
        return jsonify({"error": "outreach_id required"}), 400

    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status, recruiter_email FROM outreach WHERE id = ?", (outreach_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Outreach record not found"}), 404

    if not is_valid_email(row["recruiter_email"]):
        conn.close()
        return jsonify({"error": "Rejected placeholder recipient email"}), 400

    if row["status"] == "sent":
        conn.close()
        return jsonify({"status": "already_sent", "message": "Idempotent success"})

    cursor.execute("""
        UPDATE outreach
        SET status = 'sent', sent_at = CURRENT_TIMESTAMP, last_contacted_at = CURRENT_TIMESTAMP, provider_message_id = ?
        WHERE id = ?
    """, (provider_id, outreach_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/api/outreach/mark-replied", methods=["POST"])
@require_api_key
def mark_replied():
    data = request.json or {}
    outreach_id = data.get("outreach_id")
    reply_text = data.get("reply_text", "")
    sentiment = data.get("sentiment", "neutral")

    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO replies (outreach_id, reply_text, sentiment)
        VALUES (?, ?, ?)
    """, (outreach_id, reply_text, sentiment))
    cursor.execute("UPDATE outreach SET status = 'replied' WHERE id = ?", (outreach_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route("/api/replies/record", methods=["POST"])
@require_api_key
def record_reply():
    data = request.json or {}
    outreach_id = data.get("outreach_id")
    sender_email = data.get("sender_email")
    reply_text = data.get("reply_text", "")
    sentiment = data.get("sentiment", "neutral")
    classification = data.get("classification", "reply") # reply, bounce, opt_out, ooo

    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()

    if not outreach_id and sender_email:
        cursor.execute("SELECT id FROM outreach WHERE recruiter_email = ? ORDER BY id DESC LIMIT 1", (sender_email,))
        row = cursor.fetchone()
        if row:
            outreach_id = row["id"]

    if outreach_id:
        cursor.execute("""
            INSERT INTO replies (outreach_id, sender_email, reply_text, sentiment)
            VALUES (?, ?, ?, ?)
        """, (outreach_id, sender_email, reply_text, sentiment))

        new_status = 'replied'
        if classification == 'bounce':
            new_status = 'bounced'
        elif classification == 'opt_out':
            new_status = 'opted_out'
        elif classification == 'ooo':
            new_status = 'suppressed'

        cursor.execute("UPDATE outreach SET status = ? WHERE id = ?", (new_status, outreach_id))
        conn.commit()

    conn.close()
    return jsonify({"status": "success", "outreach_id": outreach_id, "classification": classification})

@app.route("/api/followups/due", methods=["GET"])
@require_api_key
def get_due_followups():
    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, j.title, j.company
        FROM outreach o
        JOIN jobs j ON o.job_id = j.id
        WHERE o.status = 'sent'
          AND o.followup_count < 2
          AND (julianday('now') - julianday(o.last_contacted_at)) >= 2
          AND o.status NOT IN ('replied', 'bounced', 'opted_out', 'suppressed', 'skipped_duplicate', 'needs_review')
          AND o.id NOT IN (SELECT outreach_id FROM replies)
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/followups/record-sent", methods=["POST"])
@require_api_key
def record_followup_sent():
    data = request.json or {}
    outreach_id = data.get("outreach_id")
    if not outreach_id:
        return jsonify({"error": "outreach_id required"}), 400

    tracker = OutreachTracker(DB_PATH)
    conn = tracker.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE outreach
        SET followup_count = followup_count + 1, last_contacted_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (outreach_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == "__main__":
    if not API_KEY or API_KEY == "your_secret_key":
        raise ValueError("AUTOFORGE_API_KEY must be set in .env")
    port = int(os.getenv("API_PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
