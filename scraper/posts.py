import os
import json
import logging
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from scraper.extractor import semantic_extract_job

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)
LINKEDIN_BASE = "https://www.linkedin.com"

def absolute_url(url):
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(LINKEDIN_BASE, url)
    return url

class LinkedInPostScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.storage_state_path = os.getenv("LINKEDIN_STORAGE_STATE", os.path.join(project_root, "scraper", "storage_state.json"))

    def search_posts(self, keywords: str, max_posts: int = 20) -> list:
        posts = []
        encoded_keywords = keywords.replace(" ", "%20")
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_keywords}&origin=GLOBAL_SEARCH_HEADER&datePosted=%5B%22past-24h%22%5D"

        logger.info(f"Opening browser session for LinkedIn feed content search: '{keywords}'")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"]
            )

            context_kwargs = {}
            if os.path.exists(self.storage_state_path):
                context_kwargs["storage_state"] = self.storage_state_path

            context = browser.new_context(**context_kwargs)
            page = context.new_page()

            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(6000)

                if "login" in page.url or "authwall" in page.url:
                    logger.warning("LinkedIn session expired or unauthenticated.")
                    return posts

                logger.info("Scrolling to load feed posts...")
                for _ in range(4):
                    page.evaluate("window.scrollBy(0, 1500)")
                    page.wait_for_timeout(2000)

                selectors = ["div[role='listitem']", "div.feed-shared-update-v2", "article"]
                post_cards = []
                for sel in selectors:
                    cards = page.locator(sel).all()
                    if cards:
                        post_cards = cards
                        break

                for idx, card in enumerate(post_cards[:max_posts]):
                    try:
                        # 1. Strict exclusion rules check
                        card_html = card.inner_html()
                        text = card.inner_text().strip()
                        if len(text) < 30:
                            continue

                        # Check for job listing indicators or /jobs/view/ links
                        link_elems = card.locator("a[href]").all()
                        candidate_links = []
                        mailto_links = []
                        is_job_listing = False

                        for link in link_elems:
                            href = link.get_attribute("href")
                            if href:
                                abs_href = absolute_url(href)
                                candidate_links.append(abs_href)
                                if href.startswith("mailto:"):
                                    m_email = href.replace("mailto:", "").split("?")[0]
                                    if m_email not in mailto_links:
                                        mailto_links.append(m_email)
                                if "/jobs/view/" in href or "/jobs/" in href:
                                    is_job_listing = True

                        if is_job_listing:
                            logger.info(f"Skipping dedicated job listing or /jobs/ link in card {idx}")
                            continue

                        # Check for Easy Apply or job card specific controls
                        lower_text = text.lower()
                        if "easy apply" in lower_text or "apply to this job" in lower_text:
                            # Verify if it's a dedicated job card rather than a normal feed post mentioning apply
                            if "about the job" in lower_text or "about the role" in lower_text or card.locator("button:has-text('Easy Apply')").count() > 0:
                                logger.info(f"Skipping dedicated job card with application control in card {idx}")
                                continue

                        # Try to click "see more" / "more" to expand truncated text if practical
                        try:
                            see_more_btn = card.locator("button.feed-shared-inline-show-more-text__see-more-less-toggle, button:has-text('...more'), button:has-text('see more')").first
                            if see_more_btn.is_visible():
                                see_more_btn.click(timeout=1000)
                                page.wait_for_timeout(500)
                                text = card.inner_text().strip()
                        except Exception:
                            pass

                        post_id = f"post_{idx}_{hash(text) & 0xffffffff}"

                        # Capture post URL / identifier deterministically from DOM attributes & links
                        post_url = None
                        for l in candidate_links:
                            if l and ("/feed/update/" in l or "/posts/" in l or "/activity/" in l):
                                post_url = l
                                break

                        if not post_url:
                            for sel in [
                                "a.app-aware-link[href*='/feed/update/']",
                                "a.app-aware-link[href*='/posts/']",
                                "a[href*='/feed/update/']",
                                "a[href*='/posts/']",
                                ".update-components-actor__sub-description-link",
                                ".feed-shared-actor__sub-description-link"
                            ]:
                                try:
                                    el = card.locator(sel).first
                                    if el.count() > 0:
                                        href = el.get_attribute("href")
                                        if href:
                                            abs_href = absolute_url(href)
                                            if abs_href and ("/feed/update/" in abs_href or "/posts/" in abs_href or "/activity/" in abs_href):
                                                post_url = abs_href
                                                break
                                except Exception:
                                    pass

                        if not post_url:
                            try:
                                for attr in ["data-id", "data-urn", "data-activity-id", "id"]:
                                    val = card.get_attribute(attr)
                                    if val and "activity:" in val:
                                        match = re.search(r"activity:(\d+)", val)
                                        if match:
                                            post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{match.group(1)}/"
                                            break
                            except Exception:
                                pass

                        # Try three-dot menu "Copy link to post" inspection if still not found
                        if not post_url:
                            try:
                                menu_btn = card.locator("button.feed-shared-control-menu__trigger, button[aria-label*='Control menu'], button[aria-label*='Open control menu'], button.artdeco-dropdown__trigger").first
                                if menu_btn.is_visible():
                                    menu_btn.click(timeout=1000)
                                    page.wait_for_timeout(300)

                                    copy_item = page.locator("div[role='menuitem']:has-text('Copy link to post'), li:has-text('Copy link to post'), button:has-text('Copy link to post'), .feed-shared-control-menu__item:has-text('Copy link to post')").first
                                    if copy_item.is_visible():
                                        for attr in ["href", "data-url", "data-clipboard-text", "clipboard-text"]:
                                            attr_val = copy_item.get_attribute(attr)
                                            if attr_val and ("/feed/update/" in attr_val or "/posts/" in attr_val or "/activity/" in attr_val):
                                                post_url = absolute_url(attr_val)
                                                break

                                        if not post_url:
                                            try:
                                                context.grant_permissions(['clipboard-read', 'clipboard-write'])
                                            except Exception:
                                                pass
                                            copy_item.click(timeout=1000)
                                            page.wait_for_timeout(300)
                                            clipboard_url = page.evaluate("navigator.clipboard.readText().catch(() => null)")
                                            if clipboard_url and ("/feed/update/" in clipboard_url or "/posts/" in clipboard_url or "/activity/" in clipboard_url):
                                                post_url = clipboard_url.strip()

                                    try:
                                        page.keyboard.press("Escape")
                                    except Exception:
                                        try:
                                            menu_btn.click(timeout=500)
                                        except Exception:
                                            pass
                            except Exception as menu_err:
                                logger.debug(f"Three-dot menu permalink extraction skipped/failed: {menu_err}")

                        # Missing-permalink fallback: Do not use search URL as fallback for post_url
                        if not post_url:
                            logger.warning(f"Could not extract a valid permalink for post {post_id}. Setting post_url to None.")

                        # Author name & profile URL
                        author_name = None
                        author_profile_url = next((l for l in candidate_links if "/in/" in l), None)

                        # Try to extract author name from header if possible
                        try:
                            author_elem = card.locator(".update-components-actor__title span[aria-hidden='true'], .feed-shared-actor__name").first
                            if author_elem.is_visible():
                                author_name = author_elem.inner_text().strip()
                        except Exception:
                            pass

                        # Build raw payload for Gemini
                        raw_payload = {
                            "source": "linkedin",
                            "source_post_id": post_id,
                            "post_url": post_url,
                            "author_name": author_name,
                            "author_profile_url": author_profile_url,
                            "search_keywords": keywords,
                            "post_text": text,
                            "candidate_links": candidate_links,
                            "mailto_links": mailto_links
                        }

                        # Gemini semantic extraction (exactly once per accepted post)
                        extracted = semantic_extract_job(raw_payload)

                        final_record = {
                            "source": "linkedin",
                            "source_post_id": post_id,
                            "post_url": post_url or extracted.get("post_url"),
                            "author_name": author_name or extracted.get("author_name"),
                            "author_profile_url": author_profile_url or extracted.get("author_profile_url"),
                            "posted_at": extracted.get("posted_at"),
                            "search_keywords": keywords,
                            "is_hiring_post": extracted.get("is_hiring_post", False),
                            "company": extracted.get("company"),
                            "job_title": extracted.get("job_title"),
                            "location": extracted.get("location"),
                            "work_mode": extracted.get("work_mode"),
                            "employment_type": extracted.get("employment_type"),
                            "experience_requirement": extracted.get("experience_requirement"),
                            "salary": extracted.get("salary"),
                            "notice_period": extracted.get("notice_period"),
                            "skills": extracted.get("skills", []),
                            "requirements": extracted.get("requirements", []),
                            "recruiter_name": extracted.get("recruiter_name"),
                            "recruiter_profile_url": extracted.get("recruiter_profile_url"),
                            "recruiter_email": extracted.get("recruiter_email"),
                            "contact_details": list(set(mailto_links + extracted.get("contact_details", []))),
                            "application_url": extracted.get("application_url"),
                            "description": extracted.get("description"),
                            "full_text": text
                        }
                        posts.append(final_record)
                    except Exception as e:
                        logger.warning(f"Error parsing feed post {idx}: {e}")
            finally:
                browser.close()
        return posts
