"""
Naukri Platform Handler
Handles login, job search, and application on Naukri.com.
"""

import time
import random
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class NaukriPlatform:
    BASE_URL = "https://www.naukri.com"

    def __init__(self, config: dict, browser_context):
        self.config = config
        self.ctx = browser_context
        self.creds = config["platforms"]["naukri"]
        self.profile = config["profile"]
        self.logged_in = False

    def _human_delay(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def login(self, page) -> bool:
        """Log into Naukri."""
        try:
            page.goto(f"{self.BASE_URL}/nlogin/login", timeout=30000)
            self._human_delay(2, 3)
            page.fill('input[placeholder="Enter your active Email ID / Username"]', self.creds["email"])
            self._human_delay(0.5, 1)
            page.fill('input[placeholder="Enter your password"]', self.creds["password"])
            self._human_delay(0.5, 1)
            page.click('button[type="submit"]')
            self._human_delay(3, 5)
            self.logged_in = True
            logger.info("✅ Naukri login successful")
            return True
        except Exception as e:
            logger.error(f"Naukri login failed: {e}")
            return False

    def search_jobs(self, keyword: str, location: str) -> list:
        """Search Naukri for jobs and return job list."""
        page = self.ctx.new_page()
        jobs = []
        try:
            if not self.logged_in:
                if not self.login(page):
                    return []

            keyword_slug = keyword.replace(" ", "-")
            location_slug = location.replace(" ", "-").lower()
            url = f"{self.BASE_URL}/{keyword_slug}-jobs-in-{location_slug}"
            page.goto(url, timeout=30000)
            self._human_delay(2, 4)

            for _ in range(3):
                page.keyboard.press("End")
                self._human_delay(1, 2)

            job_cards = page.locator(".jobTuple, article.jobTuple, .cust-job-tuple").all()
            logger.info(f"[Naukri] Found {len(job_cards)} job cards")

            for card in job_cards[:30]:
                try:
                    title_el = card.locator("a.title, .title").first
                    title = title_el.inner_text().strip()
                    link = title_el.get_attribute("href") or ""
                    company = card.locator(".companyInfo a, .comp-name").first.inner_text().strip()
                    loc = card.locator(".location span, .locWdth").first.inner_text().strip()

                    jobs.append({
                        "platform": "naukri",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": link,
                    })
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Naukri search error: {e}")
        finally:
            page.close()

        return jobs

    def apply_to_job(self, page, job: dict, form_filler) -> bool:
        """Navigate to Naukri job and apply."""
        try:
            page.goto(job["url"], timeout=30000)
            self._human_delay(2, 3)

            apply_btn = page.locator('button:has-text("Apply"), #apply-button, .apply-button').first
            if not apply_btn.is_visible(timeout=5000):
                logger.info(f"No apply button for: {job['title']} @ {job['company']}")
                return False

            apply_btn.click()
            self._human_delay(2, 3)

            # Naukri sometimes opens a modal or new page
            form_filler.fill_common_fields(page)
            form_filler.upload_resume(page)
            self._human_delay(1, 2)
            submitted = form_filler.click_submit(page)

            if submitted:
                logger.info(f"✅ Applied: {job['title']} @ {job['company']}")
            return submitted

        except Exception as e:
            logger.error(f"Naukri apply error: {e}")
            return False
