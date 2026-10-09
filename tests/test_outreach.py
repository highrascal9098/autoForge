import os
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from outreach.agent import OutreachAgent, get_db_connection, create_draft, approve_draft, send_approved_outreach
from outreach.generator import generate_outreach_draft, parse_json_safely
from outreach.email_sender import GmailSender
from outreach.tracker import OutreachTracker

def test_outreach_database_migration(tmp_path):
    db_file = tmp_path / "test_outreach.db"
    with patch("outreach.agent.DB_PATH", str(db_file)), \
         patch("outreach.tracker.DB_PATH", str(db_file)), \
         patch("outreach.email_sender.DB_PATH", str(db_file)):

        agent = OutreachAgent()
        conn = agent.get_db()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(outreach)")
        cols = [row["name"] for row in cursor.fetchall()]
        conn.close()

        assert "id" in cols
        assert "job_id" in cols
        assert "status" in cols
        assert "email_subject" in cols
        assert "email_body" in cols

@patch("outreach.generator.gemini_client")
def test_generate_outreach_draft_success(mock_gemini, tmp_path):
    mock_resp = MagicMock()
    mock_resp.text = '{"subject": "Inquiry", "body": "Hello", "linkedin_message": "Hi", "followup_body": "Follow up", "relevance_explanation": "Match"}'
    mock_gemini.generate_content_with_retry.return_value = mock_resp

    job = {
        "id": 1,
        "company": "TechCorp",
        "title": "Software Engineer",
        "description": "Python developer needed",
        "recruiter_email": "recruiter@techcorp.com",
        "search_keywords": "Python"
    }

    draft = generate_outreach_draft(job)
    assert draft["subject"] == "Inquiry"
    assert draft["body"] == "Hello"

def test_placeholder_email_flagged_and_blocked(tmp_path):
    db_file = tmp_path / "test_placeholder.db"
    with patch("outreach.tracker.DB_PATH", str(db_file)):
        tracker = OutreachTracker(db_file)
        tracker.init_db()

        outreach_id = tracker.save_draft(1, "recruiter@example.com", {"subject": "Test", "body": "Test"})

        # Verify status is 'needs_review' (blocked from normal approval)
        conn = tracker.get_connection()
        row = conn.execute("SELECT status FROM outreach WHERE id = ?", (outreach_id,)).fetchone()
        conn.close()
        assert row["status"] == "needs_review"

        # Attempting to approve should fail
        assert tracker.approve(outreach_id) is False

def test_distinct_opportunities_preserved(tmp_path):
    db_file = tmp_path / "test_distinct.db"
    with patch("outreach.tracker.DB_PATH", str(db_file)):
        tracker = OutreachTracker(db_file)
        tracker.init_db()

        id1 = tracker.save_draft(10, "recruiter@experion.com", {"subject": "SDET", "body": "Hi"})
        id2 = tracker.save_draft(20, "shanmukakumari.boddu@dprsolutionsinc.com", {"subject": "Playwright", "body": "Hi"})

        conn = tracker.get_connection()
        rows = conn.execute("SELECT * FROM outreach WHERE status = 'pending_approval'").fetchall()
        conn.close()

        assert len(rows) == 2
        emails = {r["recruiter_email"] for r in rows}
        assert "recruiter@experion.com" in emails
        assert "shanmukakumari.boddu@dprsolutionsinc.com" in emails

def test_duplicate_outreach_prevention(tmp_path):
    db_file = tmp_path / "test_dup.db"
    with patch("outreach.agent.DB_PATH", str(db_file)), \
         patch("outreach.tracker.DB_PATH", str(db_file)), \
         patch("outreach.generator.gemini_client") as mock_gemini:

        mock_resp = MagicMock()
        mock_resp.text = '{"subject": "Sub", "body": "Body"}'
        mock_gemini.generate_content_with_retry.return_value = mock_resp

        conn = sqlite3.connect(str(db_file))
        with open("database/schema.sql", "r") as f:
            conn.executescript(f.read())
        conn.execute("INSERT INTO jobs (external_id, title, company, recruiter_email, status) VALUES ('j1', 'Dev', 'Co', 'real@co.com', 'discovered')")
        conn.commit()
        conn.close()

        agent = OutreachAgent()
        assert agent.create_drafts(limit=5) == 1
        # Second call should not duplicate for same job_id
        assert agent.create_drafts(limit=5) == 0

@patch("sys.argv", ["main.py", "status"])
@patch("outreach.tracker.OutreachTracker.get_stats")
def test_cli_status_command(mock_stats):
    mock_stats.return_value = [{"status": "sent", "count": 1}]

    from outreach.main import main
    main()
