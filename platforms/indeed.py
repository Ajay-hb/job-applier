"""
Indeed Platform Handler
Handles login, job search, and application on Indeed.
"""

import time
import random
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class IndeedPlatform:
    BASE_URL = "https://in.indeed.com"

    def __init__(self, config: dict, browser_context):
        self.config = config
        self.ctx = browser_context
        self.creds = config["platforms"]["indeed"]
        self.profile = config["profile"]
        self.logged_in = False

    def _human_delay(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def login(self, page) -> bool:
        """Log into Indeed."""
        try:
            page.goto(f"{self.BASE_URL}/account/login", timeout=30000)
            self._human_delay(2, 3)
            page.fill('input[name="__email"]', self.creds["email"])
            self._human_delay(0.5, 1)
            page.click('button[type="submit"]')
            self._human_delay(1, 2)
            page.fill('input[name="__password"]', self.creds["password"])
            page.click('button[type="submit"]')
            self._human_delay(2, 3)
            self.logged_in = True
            logger.info("✅ Indeed login successful")
            return True
        except Exception as e:
            logger.error(f"Indeed login failed: {e}")
            return False

    def search_jobs(self, keyword: str, location: str) -> list:
        """Search Indeed for jobs and return job list."""
        page = self.ctx.new_page()
        jobs = []
        try:
            if not self.logged_in:
                if not self.login(page):
                    return []

            url = f"{self.BASE_URL}/jobs?q={quote(keyword)}&l={quote(location)}&sort=date"
            page.goto(url, timeout=30000)
            self._human_delay(2, 4)

            # Scroll to load jobs
            for _ in range(2):
                page.keyboard.press("End")
                self._human_delay(1, 2)

            job_cards = page.locator(".job_seen_beacon, .tapItem, [data-jk]").all()
            logger.info(f"[Indeed] Found {len(job_cards)} job cards")

            for card in job_cards[:30]:
                try:
                    title = card.locator("h2.jobTitle, [data-testid='jobTitle']").first.inner_text().strip()
                    company = card.locator("[data-testid='company-name'], .companyName").first.inner_text().strip()
                    loc = card.locator("[data-testid='text-location'], .companyLocation").first.inner_text().strip()
                    jk = card.get_attribute("data-jk") or ""
                    link = f"{self.BASE_URL}/viewjob?jk={jk}" if jk else ""

                    if title and company:
                        jobs.append({
                            "platform": "indeed",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": link,
                            "job_id": jk,
                        })
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Indeed search error: {e}")
        finally:
            page.close()

        return jobs

    def apply_to_job(self, page, job: dict, form_filler) -> bool:
        """Navigate to job page and apply."""
        try:
            page.goto(job["url"], timeout=30000)
            self._human_delay(2, 3)

            # Click Apply button
            apply_btn = page.locator('button:has-text("Apply now"), #indeedApplyButton, .ia-IndeedApplyButton').first
            if not apply_btn.is_visible(timeout=5000):
                logger.info(f"No direct apply for: {job['title']} @ {job['company']}")
                return False

            apply_btn.click()
            self._human_delay(2, 3)

            # Fill the form
            form_filler.fill_common_fields(page)
            form_filler.upload_resume(page)
            form_filler.fill_cover_letter(page, job)
            self._human_delay(1, 2)
            submitted = form_filler.click_submit(page)

            if submitted:
                logger.info(f"✅ Applied: {job['title']} @ {job['company']}")
            return submitted

        except Exception as e:
            logger.error(f"Indeed apply error: {e}")
            return False
