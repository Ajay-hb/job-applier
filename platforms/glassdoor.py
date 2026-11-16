"""
Glassdoor Platform Handler
Handles login, job search, and application on Glassdoor.
"""

import time
import random
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GlassdoorPlatform:
    BASE_URL = "https://www.glassdoor.co.in"

    def __init__(self, config: dict, browser_context):
        self.config = config
        self.ctx = browser_context
        self.creds = config["platforms"]["glassdoor"]
        self.profile = config["profile"]
        self.logged_in = False

    def _human_delay(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def login(self, page) -> bool:
        """Log into Glassdoor."""
        try:
            page.goto(f"{self.BASE_URL}/profile/login_input.htm", timeout=30000)
            self._human_delay(2, 3)
            page.fill('input[name="username"]', self.creds["email"])
            self._human_delay(0.5, 1)
            page.fill('input[name="password"]', self.creds["password"])
            self._human_delay(0.5, 1)
            page.click('button[type="submit"]')
            self._human_delay(2, 3)
            self.logged_in = True
            logger.info("✅ Glassdoor login successful")
            return True
        except Exception as e:
            logger.error(f"Glassdoor login failed: {e}")
            return False

    def search_jobs(self, keyword: str, location: str) -> list:
        """Search Glassdoor for jobs."""
        page = self.ctx.new_page()
        jobs = []
        try:
            if not self.logged_in:
                if not self.login(page):
                    return []

            url = (
                f"{self.BASE_URL}/Job/jobs.htm"
                f"?sc.keyword={quote(keyword)}"
                f"&locT=C&locId=1&locKeyword={quote(location)}"
                f"&sortBy=date_desc"
            )
            page.goto(url, timeout=30000)
            self._human_delay(2, 4)

            job_cards = page.locator("li.react-job-listing, [data-test='jobListing']").all()
            logger.info(f"[Glassdoor] Found {len(job_cards)} job cards")

            for card in job_cards[:20]:
                try:
                    title = card.locator("[data-test='job-title'], .jobHeader .title").first.inner_text().strip()
                    company = card.locator("[data-test='employer-name'], .job-search-key-nnf1yx").first.inner_text().strip()
                    loc = card.locator("[data-test='emp-location'], .location").first.inner_text().strip()
                    link = card.locator("a").first.get_attribute("href") or ""
                    if link and not link.startswith("http"):
                        link = self.BASE_URL + link

                    jobs.append({
                        "platform": "glassdoor",
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": link,
                    })
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Glassdoor search error: {e}")
        finally:
            page.close()

        return jobs

    def apply_to_job(self, page, job: dict, form_filler) -> bool:
        """Click Easy Apply on Glassdoor job."""
        try:
            page.goto(job["url"], timeout=30000)
            self._human_delay(2, 3)

            apply_btn = page.locator('button:has-text("Easy Apply"), button:has-text("Apply Now")').first
            if not apply_btn.is_visible(timeout=5000):
                return False

            apply_btn.click()
            self._human_delay(2, 3)

            form_filler.fill_common_fields(page)
            form_filler.upload_resume(page)
            form_filler.fill_cover_letter(page, job)
            self._human_delay(1, 2)
            submitted = form_filler.click_submit(page)

            if submitted:
                logger.info(f"✅ Applied: {job['title']} @ {job['company']}")
            return submitted

        except Exception as e:
            logger.error(f"Glassdoor apply error: {e}")
            return False
