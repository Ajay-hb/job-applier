"""
Form Filler Agent
Handles auto-filling job application forms using Playwright.
"""

import time
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FormFiller:
    """Fills and submits job application forms."""

    def __init__(self, config: dict):
        self.config = config
        self.profile = config.get("profile", {})
        self.automation = config.get("automation", {})
        self.resume_path = Path(self.automation.get("resume_file", "resumes/resume.pdf")).resolve()

    def _human_type(self, page, selector: str, text: str):
        """Type text with human-like delays."""
        try:
            page.click(selector)
            page.fill(selector, "")
            for char in text:
                page.type(selector, char, delay=random.randint(50, 150))
        except Exception as e:
            logger.warning(f"Could not type into {selector}: {e}")

    def _human_delay(self, min_s=0.5, max_s=1.5):
        time.sleep(random.uniform(min_s, max_s))

    def _safe_fill(self, page, selector: str, value: str):
        """Try to fill a field, ignore if not found."""
        try:
            if page.locator(selector).count() > 0:
                page.fill(selector, value)
                self._human_delay(0.2, 0.5)
        except Exception:
            pass

    def _safe_click(self, page, selector: str):
        """Try to click an element, ignore if not found."""
        try:
            if page.locator(selector).count() > 0:
                page.click(selector)
                self._human_delay(0.3, 0.7)
                return True
        except Exception:
            pass
        return False

    def fill_common_fields(self, page):
        """Fill the most common form fields found across platforms."""
        profile = self.profile

        field_map = {
            # Name fields
            'input[name*="name"][name*="first" i], input[placeholder*="first name" i]': profile.get("full_name", "").split()[0],
            'input[name*="last" i][name*="name" i], input[placeholder*="last name" i]': " ".join(profile.get("full_name", "").split()[1:]) or profile.get("full_name", ""),
            'input[name*="fullname" i], input[placeholder*="full name" i], input[name="name"]': profile.get("full_name", ""),
            # Contact
            'input[type="email"], input[name*="email" i]': profile.get("email", ""),
            'input[type="tel"], input[name*="phone" i], input[name*="mobile" i]': profile.get("phone", ""),
            # Location
            'input[name*="location" i], input[name*="city" i], input[placeholder*="location" i]': profile.get("location", ""),
            # URLs
            'input[name*="linkedin" i], input[placeholder*="linkedin" i]': profile.get("linkedin_url", ""),
            'input[name*="github" i], input[placeholder*="github" i]': profile.get("github_url", ""),
            'input[name*="portfolio" i], input[name*="website" i]': profile.get("portfolio_url", ""),
            # Experience
            'input[name*="experience" i], input[name*="years" i]': str(profile.get("years_of_experience", "")),
            # Salary
            'input[name*="salary" i], input[name*="ctc" i], input[name*="expected" i]': profile.get("expected_salary", ""),
            'input[name*="current.*salary" i], input[name*="current.*ctc" i]': profile.get("current_salary", ""),
            # Notice period
            'input[name*="notice" i], input[placeholder*="notice" i]': profile.get("notice_period", ""),
        }

        for selector, value in field_map.items():
            if value:
                self._safe_fill(page, selector, str(value))

    def upload_resume(self, page):
        """Upload resume file if an upload button exists."""
        if not self.resume_path.exists():
            logger.warning(f"Resume not found at: {self.resume_path}")
            return False

        upload_selectors = [
            'input[type="file"]',
            'input[name*="resume" i]',
            'input[name*="cv" i]',
            'input[accept*="pdf" i]',
        ]
        for selector in upload_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.set_input_files(selector, str(self.resume_path))
                    logger.info(f"✅ Resume uploaded via {selector}")
                    self._human_delay(1, 2)
                    return True
            except Exception:
                pass
        return False

    def fill_cover_letter(self, page, job: dict):
        """Fill cover letter field using the template."""
        try:
            template_path = Path(self.config["automation"].get("cover_letter_template", ""))
            if not template_path.exists():
                return

            with open(template_path) as f:
                template = f.read()

            profile = self.profile
            cover_letter = template.format(
                job_title=job.get("title", "this role"),
                company_name=job.get("company", "your company"),
                years_experience=profile.get("years_of_experience", "several"),
                field=profile.get("current_title", "software engineering"),
                skills="Python, software development, and problem-solving",
                full_name=profile.get("full_name", ""),
                email=profile.get("email", ""),
                phone=profile.get("phone", ""),
            )

            cl_selectors = [
                'textarea[name*="cover" i]',
                'textarea[name*="letter" i]',
                'textarea[placeholder*="cover letter" i]',
                'textarea[placeholder*="motivation" i]',
            ]
            for selector in cl_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.fill(selector, cover_letter)
                        logger.info("✅ Cover letter filled")
                        return True
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not fill cover letter: {e}")
        return False

    def handle_yes_no_questions(self, page):
        """Handle common yes/no screening questions."""
        yes_patterns = [
            'input[type="radio"][value*="yes" i]',
            'input[type="radio"][value*="true" i]',
            'input[type="radio"][value="1"]',
        ]
        for selector in yes_patterns:
            try:
                radios = page.locator(selector).all()
                for radio in radios:
                    if not radio.is_checked():
                        radio.click()
                        self._human_delay(0.3, 0.6)
            except Exception:
                pass

    def click_submit(self, page) -> bool:
        """Find and click the submit/apply button."""
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send Application")',
            'button:has-text("Continue")',
            '[data-automation="submit-application"]',
            '.submit-btn',
            '#submit-button',
        ]
        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    btn.click()
                    logger.info(f"✅ Clicked submit via: {selector}")
                    self._human_delay(2, 4)
                    return True
            except Exception:
                pass

        logger.warning("⚠️ Could not find submit button")
        return False

    def fill_and_submit(self, page, job: dict) -> bool:
        """Full flow: fill all fields and submit the application."""
        try:
            self.fill_common_fields(page)
            self._human_delay(0.5, 1)
            self.upload_resume(page)
            self._human_delay(0.5, 1)
            self.fill_cover_letter(page, job)
            self._human_delay(0.5, 1)
            self.handle_yes_no_questions(page)
            self._human_delay(1, 2)
            submitted = self.click_submit(page)
            return submitted
        except Exception as e:
            logger.error(f"Error during form fill: {e}")
            return False
