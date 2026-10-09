from scraper.posts import LinkedInPostScraper
import json
import logging

LinkedInScraper = LinkedInPostScraper

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = LinkedInScraper(headless=False)
    results = scraper.search_posts("playwright test engineer Hiring!", max_posts=5)
    print(json.dumps(results, indent=2))
