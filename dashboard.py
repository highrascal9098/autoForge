from flask import Flask, render_template_string, jsonify
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>autoForge — Autonomous Job & Outreach Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { background: #1e293b; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0_0 / 0.1); border-left: 4px solid #38bdf8; }
        .card h3 { margin: 0 0 10px 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; }
        .card .value { font-size: 28px; font-weight: bold; color: #f1f5f9; }
        section { background: #1e293b; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 6px -1px rgb(0 0_0 / 0.1); }
        h2 { margin-top: 0; color: #38bdf8; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; }
        tr:hover { background: #263348; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-sent { background: #065f46; color: #34d399; }
        .badge-drafted { background: #1e3a8a; color: #60a5fa; }
        .badge-replied { background: #831843; color: #f472b6; }
        .badge-interview { background: #3b0764; color: #c084fc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>autoForge Dashboard</span>
            <span style="font-size: 14px; color: #94a3b8;">Autonomous SDET & QA Automation Pipeline</span>
        </h1>

        <div class="stats-grid">
            <div class="card" style="border-left-color: #38bdf8;">
                <h3>Discovered Jobs</h3>
                <div class="value">{{ stats.total_jobs }}</div>
            </div>
            <div class="card" style="border-left-color: #34d399;">
                <h3>Qualified Jobs</h3>
                <div class="value">{{ stats.qualified_jobs }}</div>
            </div>
            <div class="card" style="border-left-color: #60a5fa;">
                <h3>Emails Sent</h3>
                <div class="value">{{ stats.sent_count }}</div>
            </div>
            <div class="card" style="border-left-color: #f472b6;">
                <h3>Replies Received</h3>
                <div class="value">{{ stats.reply_count }}</div>
            </div>
            <div class="card" style="border-left-color: #c084fc;">
                <h3>Interviews</h3>
                <div class="value">{{ stats.interview_count }}</div>
            </div>
            <div class="card" style="border-left-color: #fbbf24;">
                <h3>Followups Sent</h3>
                <div class="value">{{ stats.followup_total }}</div>
            </div>
        </div>

        <section>
            <h2>Upcoming Interviews</h2>
            <table>
                <thead>
                    <tr>
                        <th>Company</th>
                        <th>Role</th>
                        <th>Stage</th>
                        <th>Date & Time</th>
                        <th>Meeting URL</th>
                    </tr>
                </thead>
                <tbody>
                    {% for interview in interviews %}
                    <tr>
                        <td><strong>{{ interview.company }}</strong></td>
                        <td>{{ interview.title }}</td>
                        <td><span class="badge badge-interview">{{ interview.stage }}</span></td>
                        <td>{{ interview.interview_date }} {{ interview.interview_time }} ({{ interview.timezone }})</td>
                        <td>{% if interview.meeting_url %}<a href="{{ interview.meeting_url }}" target="_blank" style="color: #38bdf8;">Join Meeting</a>{% else %}N/A{% endif %}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="color: #94a3b8; text-align: center;">No upcoming interviews scheduled yet.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <section>
            <h2>Recent Outreach & Responses</h2>
            <table>
                <thead>
                    <tr>
                        <th>Company</th>
                        <th>Role</th>
                        <th>Recruiter Email</th>
                        <th>Status</th>
                        <th>Sent At</th>
                    </tr>
                </thead>
                <tbody>
                    {% for outreach in recent_outreach %}
                    <tr>
                        <td><strong>{{ outreach.company }}</strong></td>
                        <td>{{ outreach.title }}</td>
                        <td>{{ outreach.recruiter_email }}</td>
                        <td>
                            <span class="badge badge-{{ outreach.status }}">
                                {{ outreach.status | upper }}
                            </span>
                        </td>
                        <td>{{ outreach.sent_at or 'Pending' }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="color: #94a3b8; text-align: center;">No outreach records found yet.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <section style="margin-top: 20px; text-align: center; color: #64748b; font-size: 13px;">
            autoForge Autonomous Orchestrator &bull; SQLite Single Source of Truth &bull; Google Gemini AI &bull; n8n
        </section>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    cursor.execute("SELECT COUNT(*) as cnt FROM jobs")
    stats["total_jobs"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE match_score >= 70")
    stats["qualified_jobs"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM outreach WHERE status = 'sent'")
    stats["sent_count"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM replies")
    stats["reply_count"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM interviews")
    stats["interview_count"] = cursor.fetchone()["cnt"]

    cursor.execute("SELECT SUM(followup_count) as cnt FROM outreach")
    stats["followup_total"] = cursor.fetchone()["cnt"] or 0

    cursor.execute("""
        SELECT i.*, j.title, j.company
        FROM interviews i
        JOIN outreach o ON i.outreach_id = o.id
        JOIN jobs j ON o.job_id = j.id
        ORDER BY i.interview_date ASC LIMIT 10
    """)
    interviews = cursor.fetchall()

    cursor.execute("""
        SELECT o.*, j.title, j.company
        FROM outreach o
        JOIN jobs j ON o.job_id = j.id
        ORDER BY o.id DESC LIMIT 15
    """)
    recent_outreach = cursor.fetchall()

    conn.close()

    return render_template_string(
        DASHBOARD_TEMPLATE,
        stats=stats,
        interviews=interviews,
        recent_outreach=recent_outreach
    )

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "system": "autoForge", "version": "2.0"})

if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
