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
