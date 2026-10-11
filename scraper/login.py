<<<<<<< HEAD
import os
import time
import logging
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Use persistent context to avoid login challenges
def run_interactive_login():
    user_data_dir = os.getenv("LINKEDIN_USER_DATA_DIR", "scraper/browser_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    print("==================================================")
    print(" LinkedIn Interactive Login")
    print("==================================================")
    print("A browser will open. Log into LinkedIn manually.")
    print("Close the browser when you are finished.")
    print("==================================================")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")

        # Keep process alive until browser is closed
        try:
            while len(context.pages) > 0:
                time.sleep(1)
        except Exception:
            pass

        context.close()
        print("Login session saved to:", user_data_dir)

if __name__ == "__main__":
    run_interactive_login()
=======
"""Run on your own machine (needs a display): python scraper/login.py
Log into LinkedIn, press Enter, and copy data/linkedin/storage_state.json to the server."""
import os
from playwright.sync_api import sync_playwright

OUT = os.getenv("LINKEDIN_STORAGE_STATE", "data/linkedin/storage_state.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context()
    ctx.new_page().goto("https://www.linkedin.com/login")
    input("Log in, wait for your feed to load, then press Enter here... ")
    ctx.storage_state(path=OUT)
    browser.close()
print("Saved", OUT)
>>>>>>> origin/n8n
