import json
import os
import threading
from flask import Flask, jsonify, request
from scraper.posts import LinkedInPostScraper, SessionExpired

app = Flask(__name__)
lock = threading.Lock()  # one browser at a time
PROFILE_PATH = os.getenv("PROFILE_PATH", "profile/profile.json")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/profile")
def profile():
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.post("/scrape")
def scrape():
    body = request.get_json(force=True)
    if not lock.acquire(blocking=False):
        return jsonify(error="busy"), 429
    try:
        jobs = LinkedInPostScraper(headless=True).search_posts(
            body["query"], max_posts=int(body.get("max_posts", 15)), known_ids=set(body.get("known_ids", []))
        )
        return jsonify(jobs=jobs)
    except SessionExpired as e:
        return jsonify(error="linkedin_session_expired", detail=str(e)), 401
    finally:
        lock.release()
