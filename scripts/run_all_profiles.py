import os
import sys
import json
import time
import psycopg2
from psycopg2.extras import execute_values
from scraper.posts import scrape_linkedin_posts

def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing")
    return psycopg2.connect(db_url)

def load_profile():
    profile_path = 'profile/profile.json'
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"{profile_path} does not exist")
    with open(profile_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_search_queries(profile):
    configured_queries = profile.get('search_queries', [])
    target_roles = profile.get('preferences', {}).get('target_roles', [])
    
    queries = list(configured_queries)
    
    # Expand with role hiring queries
    for role in target_roles:
        q = f"{role} hiring"
        if q not in queries:
            queries.append(q)
            
    # Add variations for high-priority automation/playwright roles
    automation_keywords = ["Playwright hiring", "SDET hiring email", "Automation Engineer hiring email"]
    for kw in automation_keywords:
        if kw not in queries:
            queries.append(kw)
            
    return queries

def save_jobs_to_db(jobs):
    if not jobs:
        return 0
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
    INSERT INTO jobs (
        id, query, post_url, author_name, author_title,
        content, posted_at_raw, discovered_at, status,
        extracted_role, extracted_email
    ) VALUES %s
    ON CONFLICT (post_url) DO UPDATE SET
        extracted_email = COALESCE(EXCLUDED.extracted_email, jobs.extracted_email),
        extracted_role = COALESCE(EXCLUDED.extracted_role, jobs.extracted_role),
        author_name = COALESCE(EXCLUDED.author_name, jobs.author_name)
    """
    
    values = [
        (
            j['id'], j['query'], j['post_url'], j.get('author_name'),
            j.get('author_title'), j['content'], j.get('posted_at_raw', 'past-24h'),
            'NOW()', 'discovered', j.get('extracted_role'), j.get('extracted_email')
        )
        for j in jobs
    ]
    
    execute_values(cur, query, values)
    conn.commit()
    inserted_or_updated = len(values)
    cur.close()
    conn.close()
    return inserted_or_updated

def main():
    print("=== AutoForge Multi-Profile Job Scraper Started ===")
    profile = load_profile()
    queries = generate_search_queries(profile)
    
    print(f"Candidate: {profile.get('name')}")
    print(f"Generated {len(queries)} dynamic search queries across all target roles.")
    
    total_jobs_saved = 0
    queries_processed = 0
    unique_emails_collected = set()
    target_minimum_emails = 50
    
    for q in queries:
        queries_processed += 1
        print(f"\n--- [{queries_processed}/{len(queries)}] Processing query: '{q}' ---")
        
        try:
            jobs = scrape_linkedin_posts(query=q, max_posts=15, date_filter="past-24h")
            # Fallback to past-week if past-24h returns 0 for a query to maximize email yield
            if not jobs:
                print(f"No jobs found for past-24h, trying past-week for '{q}'...")
                jobs = scrape_linkedin_posts(query=q, max_posts=10, date_filter="past-week")
                
            new_emails_in_query = 0
            for j in jobs:
                email = j.get('extracted_email')
                if email and email not in unique_emails_collected:
                    unique_emails_collected.add(email)
                    new_emails_in_query += 1
                    
            count = save_jobs_to_db(jobs)
            total_jobs_saved += count
            print(f"Saved/Updated {count} records (New unique emails in this query: {new_emails_in_query}).")
            print(f"Total unique emails collected so far: {len(unique_emails_collected)}")
            
            # Stop early if we comfortably exceeded target yield to respect rate limits
            if len(unique_emails_collected) >= 75:
                print(f"Reached target quota with {len(unique_emails_collected)} unique recruiter emails!")
                break
                
            time.sleep(2)  # Polite interval between queries
            
        except Exception as e:
            print(f"Error processing query '{q}': {e}")
            
    print("\n================ Summary ================")
    print(f"Total queries processed: {queries_processed}")
    print(f"Total unique emails extracted: {len(unique_emails_collected)}")
    print(f"Total job records synced to DB: {total_jobs_saved}")
    print("========================================")

if __name__ == '__main__':
    main()
