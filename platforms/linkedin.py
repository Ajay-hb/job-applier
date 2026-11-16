"""
LinkedIn Platform Handler
Handles login, job search, and Easy Apply on LinkedIn.
"""

import time
import random
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class LinkedInPlatform:
    BASE_URL = "https://www.linkedin.com"

    def __init__(self, config: dict, browser_context):
        self.config = config
        self.ctx = browser_context
        self.creds = config["platforms"]["linkedin"]
        self.profile = config["profile"]
        self.logged_in = False

    def _human_delay(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def login(self, page) -> bool:
        """Log into LinkedIn."""
        try:
            page.goto(f"{self.BASE_URL}/login", timeout=30000)
            self._human_delay(1, 2)
            page.fill('#username', self.creds["email"])
            self._human_delay(0.5, 1)
            page.fill('#password', self.creds["password"])
            self._human_delay(0.5, 1)
            page.click('button[type="submit"]')
            page.wait_for_url("**/feed**", timeout=15000)
            self.logged_in = True
            logger.info("✅ LinkedIn login successful")
            return True
        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False

    def search_jobs(self, keyword: str, location: str) -> list:
        """Search for jobs and return list of job dicts."""
        page = self.ctx.new_page()
        jobs = []
        try:
            if not self.logged_in:
                if not self.login(page):
                    return []

            # Build search URL
            easy_apply = "&f_LF=f_AL" if self.creds.get("easy_apply_only") else ""
            url = (
                f"{self.BASE_URL}/jobs/search/"
                f"?keywords={quote(keyword)}"
                f"&location={quote(location)}"
                f"{easy_apply}"
                f"&sortBy=DD"
            )
            page.goto(url, timeout=30000)
            self._human_delay(2, 4)

            # Scroll to load more jobs
            for _ in range(3):
                page.keyboard.press("End")
                self._human_delay(1, 2)

            # Extract job cards
            job_cards = page.locator(".job-search-card, .jobs-search__results-list li, [data-occludable-job-id]").all()
            logger.info(f"[LinkedIn] Found {len(job_cards)} job cards")

            for card in job_cards[:30]:
                try:
                    title = card.locator(".job-search-card__title, .base-search-card__title").first.inner_text().strip()
                    company = card.locator(".job-search-card__company-name, .base-search-card__subtitle").first.inner_text().strip()
                    loc = card.locator(".job-search-card__location, .job-search-card__location").first.inner_text().strip()
                    link = card.locator("a").first.get_attribute("href") or ""
                    if link and not link.startswith("http"):
                        link = self.BASE_URL + link

                    jobs.append({
                        "platform": "linkedin",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": link.split("?")[0],
                        "easy_apply": "easy_apply_only" in url,
                    })
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"LinkedIn search error: {e}")
        finally:
            page.close()

        return jobs

    def apply_to_job(self, page, job: dict, form_filler) -> bool:
        """Navigate to job and attempt Easy Apply."""
        try:
            page.goto(job["url"], timeout=30000)
            self._human_delay(2, 3)

            # Click Easy Apply button
            easy_apply_btn = page.locator('button:has-text("Easy Apply"), .jobs-apply-button').first
            if not easy_apply_btn.is_visible(timeout=5000):
                logger.info(f"No Easy Apply for: {job['title']} @ {job['company']}")
                return False

            easy_apply_btn.click()
            self._human_delay(1, 2)

            # Handle multi-step modal
            max_steps = 10
            for step in range(max_steps):
                form_filler.fill_common_fields(page)
                form_filler.upload_resume(page)
                form_filler.fill_cover_letter(page, job)
                form_filler.handle_yes_no_questions(page)
                self._human_delay(0.5, 1)

                # Try Next or Submit
                next_btn = page.locator('button:has-text("Next"), button:has-text("Review"), button:has-text("Continue")').first
                submit_btn = page.locator('button:has-text("Submit application"), button:has-text("Submit")').first

                if submit_btn.is_visible(timeout=2000):
                    submit_btn.click()
                    self._human_delay(2, 3)
                    logger.info(f"✅ Applied: {job['title']} @ {job['company']}")
                    return True
                elif next_btn.is_visible(timeout=2000):
                    next_btn.click()
                    self._human_delay(1, 2)
                else:
                    break

        except Exception as e:
            logger.error(f"LinkedIn apply error: {e}")

        return False
