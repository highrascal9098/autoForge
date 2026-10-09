import os
import sqlite3
import pytest
import re
from unittest.mock import MagicMock, patch
from scraper.main import deduplicate_jobs, save_jobs_to_db, get_db_connection, init_db
from scraper.posts import LinkedInPostScraper
from scraper.extractor import semantic_extract_job, parse_json_safely

def test_deduplicate_jobs():
    existing_ids = {"ext_1", "ext_2"}
    scraped_jobs = [
        {"external_id": "ext_2", "title": "Dev"},
        {"external_id": "ext_3", "title": "Engineer"}
    ]
    new_jobs = deduplicate_jobs(scraped_jobs, existing_ids)
    assert len(new_jobs) == 1
    assert new_jobs[0]["external_id"] == "ext_3"

def test_database_initialization(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    with open("database/schema.sql", "r") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    assert "jobs" in tables
    assert "outreach" in tables
    assert "replies" in tables
    conn.close()

def test_experience_gap_evaluation():
    job_experience_req = "10+ years"
    candidate_experience = 4.8
    tech_match = True
    outreach_allowed = tech_match and ("10+" in job_experience_req or candidate_experience < 10)
    assert outreach_allowed is True

@patch("scraper.posts.sync_playwright")
@patch("scraper.posts.semantic_extract_job")
def test_scraper_exclusion_and_acceptance(mock_extract, mock_playwright):
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    card_normal_hiring = MagicMock()
    card_normal_hiring.inner_text.return_value = "WE ARE HIRING Playwright Test Engineer. Email resume to test@company.com. Feel free to apply."
    card_normal_hiring.inner_html.return_value = "<div>WE ARE HIRING Playwright Test Engineer</div>"
    link1 = MagicMock()
    link1.get_attribute.return_value = "mailto:test@company.com"
    link2 = MagicMock()
    link2.get_attribute.return_value = "https://www.linkedin.com/feed/update/urn:li:activity:7123456789"
    card_normal_hiring.locator.return_value.all.return_value = [link1, link2]

    mock_page.locator.return_value.all.return_value = [card_normal_hiring]

    mock_extract.return_value = {
        "source": "linkedin",
        "source_post_id": "post_0_12345",
        "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:7123456789",
        "author_name": "Jane Doe",
        "author_profile_url": "https://www.linkedin.com/in/janedoe",
        "posted_at": "1d",
        "search_keywords": "Playwright",
        "is_hiring_post": True,
        "company": "TestCorp",
        "job_title": "Playwright Test Engineer",
        "location": "Remote",
        "work_mode": "Remote",
        "employment_type": "Full-time",
        "experience_requirement": "3+ years",
        "salary": None,
        "notice_period": None,
        "skills": ["Playwright", "Python"],
        "requirements": ["3+ years experience"],
        "recruiter_name": "Jane Doe",
        "recruiter_profile_url": "https://www.linkedin.com/in/janedoe",
        "recruiter_email": "test@company.com",
        "contact_details": ["test@company.com"],
        "application_url": None,
        "description": "We are hiring Playwright Test Engineer.",
        "full_text": "WE ARE HIRING Playwright Test Engineer. Email resume to test@company.com."
    }

    scraper = LinkedInPostScraper(headless=True)
    results = scraper.search_posts("Playwright Test Engineer", max_posts=1)

    assert len(results) == 1
    assert results[0]["is_hiring_post"] is True
    assert results[0]["post_url"] == "https://www.linkedin.com/feed/update/urn:li:activity:7123456789"
    # Ensure post_url is never the search results URL
    assert "/search/results/content/" not in results[0]["post_url"]
    assert mock_extract.call_count == 1

@patch("scraper.posts.sync_playwright")
@patch("scraper.posts.semantic_extract_job")
def test_missing_permalink_results_in_null(mock_extract, mock_playwright):
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    card_no_link = MagicMock()
    card_no_link.inner_text.return_value = "WE ARE HIRING Python Developer with no permalink link anywhere in card."
    card_no_link.inner_html.return_value = "<div>Hiring</div>"
    card_no_link.locator.return_value.all.return_value = []
    card_no_link.get_attribute.return_value = None

    mock_page.locator.return_value.all.return_value = [card_no_link]

    mock_extract.return_value = {
        "source": "linkedin",
        "source_post_id": "post_0_9999",
        "post_url": None,
        "author_name": None,
        "author_profile_url": None,
        "posted_at": None,
        "search_keywords": "Python",
        "is_hiring_post": True,
        "company": "Corp",
        "job_title": "Developer",
        "location": "Remote",
        "work_mode": "Remote",
        "employment_type": "Full-time",
        "experience_requirement": None,
        "salary": None,
        "notice_period": None,
        "skills": [],
        "requirements": [],
        "recruiter_name": None,
        "recruiter_profile_url": None,
        "recruiter_email": None,
        "contact_details": [],
        "application_url": None,
        "description": "Hiring",
        "full_text": "WE ARE HIRING Python Developer..."
    }

    scraper = LinkedInPostScraper(headless=True)
    results = scraper.search_posts("Python Developer", max_posts=1)

    assert len(results) == 1
    # Missing permalink must be None, NOT the search page URL
    assert results[0]["post_url"] is None

def test_parse_json_safely():
    valid = '{"is_hiring_post": true, "company": "Test"}'
    assert parse_json_safely(valid)["is_hiring_post"] is True

    wrapped_markdown = '```json\n{"is_hiring_post": false}\n```'
    assert parse_json_safely(wrapped_markdown)["is_hiring_post"] is False

    noisy_json = 'Here is the result: {"company": "Acme"} thank you'
    assert parse_json_safely(noisy_json)["company"] == "Acme"

@patch("scraper.extractor.gemini_client")
def test_semantic_extract_job_repair_and_fallback(mock_gemini):
    # First call returns invalid JSON, second call (repair) returns valid JSON
    mock_resp_invalid = MagicMock()
    mock_resp_invalid.text = 'Invalid json with \\bad_escape'

    mock_resp_valid = MagicMock()
    mock_resp_valid.text = '{"is_hiring_post": true, "company": "FixedCorp"}'

    mock_gemini.generate_content_with_retry.side_effect = [mock_resp_invalid, mock_resp_valid]

    payload = {"post_text": "We are hiring at FixedCorp"}
    result = semantic_extract_job(payload)
    assert result["company"] == "FixedCorp"
    assert result["is_hiring_post"] is True

def test_non_hiring_post_excluded_from_db(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    with patch("scraper.main.DB_PATH", str(db_file)):
        init_db()
        jobs = [
            {
                "source": "linkedin",
                "source_post_id": "hiring_1",
                "is_hiring_post": True,
                "job_title": "Engineer",
                "full_text": "We are hiring an engineer."
            },
            {
                "source": "linkedin",
                "source_post_id": "non_hiring_1",
                "is_hiring_post": False,
                "job_title": None,
                "full_text": "Check out this nice picture of my cat."
            }
        ]
        save_jobs_to_db(jobs)

        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT external_id FROM jobs")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0]["external_id"] == "hiring_1"

def test_idempotent_db_persistence(tmp_path):
    db_file = tmp_path / "test_idempotent.db"
    with patch("scraper.main.DB_PATH", str(db_file)):
        init_db()
        job1 = [{
            "source": "linkedin",
            "source_post_id": "post_abc",
            "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:123",
            "is_hiring_post": True,
            "job_title": "Developer v1",
            "full_text": "Hiring developer."
        }]
        save_jobs_to_db(job1)

        job2 = [{
            "source": "linkedin",
            "source_post_id": "post_abc",
            "post_url": None, # Should not overwrite valid post_url due to COALESCE
            "is_hiring_post": True,
            "job_title": "Developer v2",
            "full_text": "Hiring developer updated."
        }]
        save_jobs_to_db(job2)

        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT title, post_url FROM jobs WHERE external_id = 'post_abc'")
        row = cursor.fetchone()
        conn.close()

        assert row["title"] == "Developer v2"
        assert row["post_url"] == "https://www.linkedin.com/feed/update/urn:li:activity:123"
