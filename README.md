# Auto Job Applier 🤖

A multi-platform automated job application bot built with Python + Playwright.

## Features
- 🔍 Searches jobs on **LinkedIn, Indeed, Naukri, Glassdoor**
- 📝 Auto-fills application forms (name, email, phone, resume, cover letter)
- 📎 Uploads your resume automatically
- 🧠 Template-based cover letter generation
- 📊 SQLite tracker to avoid duplicate applications
- 🌐 Web dashboard to monitor all applications
- ⏰ Scheduler for daily automated runs
- 🛡️ Human-like delays to avoid detection

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure your profile
Edit `config/settings.yaml`:
- Fill in your **personal details** (name, email, phone, etc.)
- Add your **platform credentials**
- Set your **job search keywords** and locations
- Set your **resume path**

### 3. Add your resume
Copy your resume PDF to `resumes/resume.pdf`

### 4. Run
```bash
# Interactive menu
python main.py

# Or directly:
python main.py run        # Run application session
python main.py dashboard  # Open web dashboard
python main.py stats      # Show application stats
```

---

## Project Structure
```
job-applier/
├── main.py                  # Entry point & orchestrator
├── requirements.txt
├── config/
│   ├── settings.yaml        # ← Edit this first!
│   └── cover_letter_template.txt
├── resumes/
│   └── resume.pdf           # ← Put your resume here
├── agents/
│   ├── scraper.py           # Job search across platforms
│   └── form_filler.py       # Auto form filling
├── platforms/
│   ├── linkedin.py
│   ├── indeed.py
│   ├── naukri.py
│   └── glassdoor.py
├── tracker/
│   ├── db.py                # SQLite application tracker
│   └── applications.db      # Auto-created
├── dashboard/
│   └── app.py               # Flask web dashboard
└── logs/                    # Run logs & error screenshots
```

---

## Configuration Guide

### Job Search Keywords
```yaml
search:
  keywords:
    - "Python Developer"
    - "Backend Engineer"
  locations:
    - "Bangalore"
    - "Remote"
```

### Blacklisting
```yaml
search:
  blacklisted_companies:
    - "Spam Corp"
  blacklisted_keywords:
    - "unpaid"
```

### Daily Scheduler
```yaml
scheduler:
  enabled: true
  run_at: "09:00"
  days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
```

---

## Dashboard
Run `python main.py dashboard` and open http://localhost:5000

The dashboard shows:
- Total applications, interviews, rejections, offers
- Application list with filters by status/platform
- Auto-refreshes every 30 seconds

---

## Tips
- Set `headless: false` while testing to watch the browser
- Set `headless: true` for background runs
- Start with `daily_limit: 5` to test before scaling up
- LinkedIn Easy Apply works best — enable it first
- Keep `delay_between_apps: 30` to avoid getting flagged

---

## ⚠️ Disclaimer
Use responsibly. Automated job applications should complement your manual applications, not replace them. Always review job fit before enabling auto-apply at scale. Some platforms may flag or ban accounts for automation — start slow.
