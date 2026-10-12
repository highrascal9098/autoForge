"""Interactive LinkedIn login tool to generate authenticated Playwright storage state.
Usage: python -m scraper.login
"""
import os
from playwright.sync_api import sync_playwright

def main():
    out_path = os.getenv("LINKEDIN_STORAGE_STATE", "data/linkedin/storage_state.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    print(f"[*] Opening browser for LinkedIn login...")
    print(f"[*] Target storage state path: {out_path}")

    with sync_playwright() as p:
        # Try launching system Chrome to avoid STATUS_BREAKPOINT crashes on Windows
        browser = None
        for channel in ["chrome", "msedge", ""]:
            try:
                launch_kwargs = {
                    "headless": False,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-dev-shm-usage"
                    ]
                }
                if channel:
                    launch_kwargs["channel"] = channel
                browser = p.chromium.launch(**launch_kwargs)
                break
            except Exception:
                continue

        if not browser:
            browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto("https://www.linkedin.com/login", timeout=60000)
            print("\n[+] Browser opened. Please log into LinkedIn manually.")
            print("[+] Once you are fully logged in and can see your LinkedIn feed, return here and press Enter.")
            input("\nPress Enter AFTER your LinkedIn feed has successfully loaded... ")

            context.storage_state(path=out_path)
            print(f"[+] Success! Authentication storage state saved to: {out_path}")
        except Exception as e:
            print(f"[-] Error during login capture: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
