"""
Job Scraper Agent
Searches for jobs across multiple platforms based on config settings.
"""

import time
import random
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class JobScraper:
    """Collects job listings from configured platforms."""

    def __init__(self, config: dict, browser_context):
        self.config = config
        self.ctx = browser_context
        self.search_cfg = config.get("search", {})
        self.keywords = self.search_cfg.get("keywords", [])
        self.locations = self.search_cfg.get("locations", [])
        self.blacklisted_companies = [c.lower() for c in self.search_cfg.get("blacklisted_companies", [])]
        self.blacklisted_keywords = [k.lower() for k in self.search_cfg.get("blacklisted_keywords", [])]

    def _is_blacklisted(self, job: dict) -> bool:
        company = job.get("company", "").lower()
        title = job.get("title", "").lower()
        if any(b in company for b in self.blacklisted_companies):
            return True
        if any(b in title for b in self.blacklisted_keywords):
            return True
        return False

    def _human_delay(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def scrape_linkedin(self) -> list:
        """Scrape LinkedIn job listings."""
        from platforms.linkedin import LinkedInPlatform
        cfg = self.config["platforms"].get("linkedin", {})
        if not cfg.get("enabled"):
            return []
        platform = LinkedInPlatform(self.config, self.ctx)
        jobs = []
        for keyword in self.keywords:
            for location in self.locations:
                logger.info(f"[LinkedIn] Searching: '{keyword}' in '{location}'")
                found = platform.search_jobs(keyword, location)
                jobs.extend(found)
                self._human_delay(2, 4)
        return [j for j in jobs if not self._is_blacklisted(j)]

    def scrape_indeed(self) -> list:
        """Scrape Indeed job listings."""
        from platforms.indeed import IndeedPlatform
        cfg = self.config["platforms"].get("indeed", {})
        if not cfg.get("enabled"):
            return []
        platform = IndeedPlatform(self.config, self.ctx)
        jobs = []
        for keyword in self.keywords:
            for location in self.locations:
                logger.info(f"[Indeed] Searching: '{keyword}' in '{location}'")
                found = platform.search_jobs(keyword, location)
                jobs.extend(found)
                self._human_delay(2, 4)
        return [j for j in jobs if not self._is_blacklisted(j)]

    def scrape_naukri(self) -> list:
        """Scrape Naukri job listings."""
        from platforms.naukri import NaukriPlatform
        cfg = self.config["platforms"].get("naukri", {})
        if not cfg.get("enabled"):
            return []
        platform = NaukriPlatform(self.config, self.ctx)
        jobs = []
        for keyword in self.keywords:
            for location in self.locations:
                logger.info(f"[Naukri] Searching: '{keyword}' in '{location}'")
                found = platform.search_jobs(keyword, location)
                jobs.extend(found)
                self._human_delay(2, 4)
        return [j for j in jobs if not self._is_blacklisted(j)]

    def scrape_glassdoor(self) -> list:
        """Scrape Glassdoor job listings."""
        from platforms.glassdoor import GlassdoorPlatform
        cfg = self.config["platforms"].get("glassdoor", {})
        if not cfg.get("enabled"):
            return []
        platform = GlassdoorPlatform(self.config, self.ctx)
        jobs = []
        for keyword in self.keywords:
            for location in self.locations:
                logger.info(f"[Glassdoor] Searching: '{keyword}' in '{location}'")
                found = platform.search_jobs(keyword, location)
                jobs.extend(found)
                self._human_delay(2, 4)
        return [j for j in jobs if not self._is_blacklisted(j)]

    def scrape_all(self) -> list:
        """Run all enabled platform scrapers and return combined unique job list."""
        all_jobs = []
        scrapers = [
            self.scrape_linkedin,
            self.scrape_indeed,
            self.scrape_naukri,
            self.scrape_glassdoor,
        ]
        for scraper_fn in scrapers:
            try:
                jobs = scraper_fn()
                all_jobs.extend(jobs)
                logger.info(f"  → {len(jobs)} jobs collected from {scraper_fn.__name__}")
            except Exception as e:
                logger.error(f"Error in {scraper_fn.__name__}: {e}")

        # Deduplicate by URL
        seen = set()
        unique = []
        for job in all_jobs:
            url = job.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(job)

        logger.info(f"Total unique jobs found: {len(unique)}")
        return unique
