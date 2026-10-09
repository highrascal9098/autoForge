import os
import json
import sqlite3
import logging
import argparse
from dotenv import load_dotenv
from scraper.posts import LinkedInPostScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("autoForge")

DB_PATH = os.getenv("DB_PATH", "database/jobs.db")
PROFILE_PATH = "profile/profile.json"

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    schema_path = "database/schema.sql"
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

    # Ensure any newly added columns exist if jobs table already existed
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    new_cols = [
        ("notice_period", "TEXT"),
        ("contact_details", "TEXT"),
        ("source_post_id", "TEXT"),
        ("post_url", "TEXT"),
        ("job_url", "TEXT"),
        ("work_mode", "TEXT"),
        ("employment_type", "TEXT"),
        ("experience_requirement", "TEXT"),
        ("salary", "TEXT"),
        ("raw_description", "TEXT"),
        ("requirements", "TEXT"),
        ("skills", "TEXT"),
        ("recruiter_profile_url", "TEXT"),
        ("application_url", "TEXT"),
        ("posted_at", "TEXT"),
        ("search_keywords", "TEXT")
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
                logger.info(f"Added missing column {col_name} to jobs table.")
            except Exception as e:
                logger.warning(f"Could not add column {col_name}: {e}")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def save_jobs_to_db(jobs):
    """
    Persists extracted structured job records into SQLite idempotently using source_post_id / external_id.
    Only saves hiring posts (is_hiring_post = True). Skips non-hiring posts.
    Serializes arrays (requirements, skills, contact_details) as JSON strings.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    saved_count = 0
    skipped_count = 0
    for job in jobs:
        if not job.get("is_hiring_post", False):
            logger.info(f"Skipping non-hiring post {job.get('source_post_id')} (not a hiring opportunity).")
            skipped_count += 1
            continue

        ext_id = job.get("source_post_id") or job.get("external_id")
        if not ext_id:
            continue

        cursor.execute("""
            INSERT INTO jobs (
                external_id, source, source_post_id, post_url, job_url, title, company,
                location, work_mode, employment_type, experience_requirement, salary,
                notice_period, description, full_text, raw_description, requirements, skills,
                contact_details, recruiter_name, recruiter_profile_url, recruiter_email,
                application_url, posted_at, search_keywords, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                post_url = COALESCE(excluded.post_url, post_url),
                job_url = COALESCE(excluded.job_url, job_url),
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                work_mode = excluded.work_mode,
                employment_type = excluded.employment_type,
                experience_requirement = excluded.experience_requirement,
                salary = excluded.salary,
                notice_period = excluded.notice_period,
                description = excluded.description,
                full_text = excluded.full_text,
                raw_description = excluded.raw_description,
                requirements = excluded.requirements,
                skills = excluded.skills,
                contact_details = excluded.contact_details,
                recruiter_name = excluded.recruiter_name,
                recruiter_profile_url = excluded.recruiter_profile_url,
                recruiter_email = excluded.recruiter_email,
                application_url = excluded.application_url,
                posted_at = excluded.posted_at,
                search_keywords = excluded.search_keywords,
                status = excluded.status
        """, (
            ext_id,
            job.get("source", "linkedin"),
            job.get("source_post_id"),
            job.get("post_url"),
            job.get("job_url"),
            job.get("job_title"),
            job.get("company"),
            job.get("location"),
            job.get("work_mode"),
            job.get("employment_type"),
            job.get("experience_requirement"),
            job.get("salary"),
            job.get("notice_period"),
            job.get("description"),
            job.get("full_text"),
            job.get("full_text"), # raw_description
            json.dumps(job.get("requirements", [])),
            json.dumps(job.get("skills", [])),
            json.dumps(job.get("contact_details", [])),
            job.get("recruiter_name"),
            job.get("recruiter_profile_url"),
            job.get("recruiter_email"),
            job.get("application_url"),
            job.get("posted_at"),
            job.get("search_keywords"),
            'discovered'
        ))
        saved_count += 1

    conn.commit()
    conn.close()
    logger.info(f"Successfully persisted {saved_count} hiring post(s) to SQLite database ({DB_PATH}). Skipped {skipped_count} non-hiring post(s).")

def deduplicate_jobs(scraped_jobs, existing_ids):
    """
    Filters out scraped jobs whose external_id is already in existing_ids.
    """
    return [job for job in scraped_jobs if (job.get("source_post_id") or job.get("external_id")) not in existing_ids]

def load_profile():
    if not os.path.exists(PROFILE_PATH):
        return {}
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_scraper_to_json(keywords=None, location="Remote", max_posts=15):
    """
    Runs Playwright scraper and Gemini extraction ONCE per post via posts.py,
    returns structured job records, and persists hiring posts to SQLite.
    When keywords is omitted (None), loads profile/profile.json and runs every entry in search_queries.
    """
    scraper = LinkedInPostScraper(headless=True)

    queries = []
    if keywords:
        queries = [keywords]
    else:
        profile = load_profile()
        queries = profile.get("search_queries", [])

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT external_id FROM jobs")
    existing_ids = {row["external_id"] for row in cursor.fetchall() if row["external_id"]}
    conn.close()

    all_jobs = []
    seen_ids = set(existing_ids)
    for q in queries:
        logger.info(f"Running scrape for query: {q}")
        jobs = scraper.search_posts(q, max_posts=max_posts)
        if jobs:
            # Tag jobs with search_keywords
            for j in jobs:
                if not j.get("search_keywords"):
                    j["search_keywords"] = q
            new_jobs = deduplicate_jobs(jobs, seen_ids)
            for j in new_jobs:
                ext_id = j.get("source_post_id") or j.get("external_id")
                if ext_id:
                    seen_ids.add(ext_id)
            if new_jobs:
                save_jobs_to_db(new_jobs)
                all_jobs.extend(new_jobs)

    return all_jobs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LinkedIn post scraper, Gemini extraction, and SQLite persistence")
    parser.add_argument("--keywords", type=str, default=None, help="Job search keywords")
    parser.add_argument("--location", type=str, default="Remote", help="Job location")
    parser.add_argument("--max-posts", type=int, default=15, help="Maximum posts to scrape")
    parser.add_argument("--json", action="store_true", default=True, help="Output JSON to stdout")
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run browser in headless mode (use --no-headless to show browser)"
    )
    args = parser.parse_args()

    jobs = run_scraper_to_json(keywords=args.keywords, location=args.location, max_posts=args.max_posts)
    print(json.dumps(jobs, indent=2))
