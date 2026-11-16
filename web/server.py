"""
Web Server — Flask backend for the Job Applier web UI.
Serves the SPA and exposes REST APIs for config, jobs, automation control.
"""

import sys
import os
import yaml
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tracker.db import (
    init_db, get_all_applications, get_stats,
    update_status, add_application, get_all_applications
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

CONFIG_PATH = ROOT / "config" / "settings.yaml"
RESUME_DIR  = ROOT / "resumes"
LOG_DIR     = ROOT / "logs"

# Global automation state
automation_state = {
    "running": False,
    "log": [],
    "applied": 0,
    "found": 0,
    "current_job": "",
    "started_at": None,
}
automation_lock = threading.Lock()


# ─── Helper ──────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def save_config(data: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

def log_msg(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    automation_state["log"].append(entry)
    if len(automation_state["log"]) > 500:
        automation_state["log"] = automation_state["log"][-500:]
    print(entry)


# ─── Pages ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── Config API ──────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def set_config():
    data = request.json
    save_config(data)
    return jsonify({"ok": True, "message": "Config saved successfully"})

@app.route("/api/config/profile", methods=["POST"])
def save_profile():
    cfg = load_config()
    cfg["profile"] = request.json
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/config/search", methods=["POST"])
def save_search():
    cfg = load_config()
    cfg["search"] = request.json
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/config/platforms", methods=["POST"])
def save_platforms():
    cfg = load_config()
    cfg["platforms"] = request.json
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/config/automation", methods=["POST"])
def save_automation():
    cfg = load_config()
    cfg["automation"] = request.json
    save_config(cfg)
    return jsonify({"ok": True})


# ─── Resume Upload ────────────────────────────────────────────────────────────

@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"ok": False, "error": "No file provided"}), 400
    file = request.files["resume"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"ok": False, "error": "Only PDF files accepted"}), 400
    RESUME_DIR.mkdir(exist_ok=True)
    path = RESUME_DIR / "resume.pdf"
    file.save(str(path))
    return jsonify({"ok": True, "message": "Resume uploaded successfully"})

@app.route("/api/resume/status")
def resume_status():
    path = RESUME_DIR / "resume.pdf"
    return jsonify({
        "exists": path.exists(),
        "size_kb": round(path.stat().st_size / 1024, 1) if path.exists() else 0,
        "updated": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if path.exists() else None
    })


# ─── Applications API ─────────────────────────────────────────────────────────

@app.route("/api/stats")
def stats():
    return jsonify(get_stats())

@app.route("/api/applications")
def applications():
    status   = request.args.get("status")
    platform = request.args.get("platform")
    limit    = request.args.get("limit", type=int)
    return jsonify(get_all_applications(limit=limit, platform=platform, status=status))

@app.route("/api/applications/update", methods=["POST"])
def update_app_status():
    data = request.json
    update_status(data["job_url"], data["status"], data.get("notes", ""))
    return jsonify({"ok": True})


# ─── Automation Control ───────────────────────────────────────────────────────

def run_automation_thread(config):
    """Background thread that runs the Playwright automation."""
    global automation_state
    try:
        from playwright.sync_api import sync_playwright
        import time, random

        sys.path.insert(0, str(ROOT))
        from agents.form_filler import FormFiller
        from tracker.db import is_already_applied, add_application, add_skipped

        auto_cfg   = config.get("automation", {})
        max_apps   = auto_cfg.get("max_daily_applications", 50)
        delay_sec  = auto_cfg.get("delay_between_apps", 30)
        headless   = auto_cfg.get("headless", True)
        slow_mo    = auto_cfg.get("slow_mo", 300)
        applied    = 0

        log_msg("🚀 Starting automation session...")
        automation_state["started_at"] = datetime.now().isoformat()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )

            from agents.scraper import JobScraper
            scraper     = JobScraper(config, context)
            form_filler = FormFiller(config)

            log_msg("🔍 Searching jobs across platforms...")
            jobs = scraper.scrape_all()
            automation_state["found"] = len(jobs)
            log_msg(f"✅ Found {len(jobs)} unique jobs")

            for job in jobs:
                if not automation_state["running"]:
                    log_msg("⛔ Stopped by user")
                    break
                if applied >= max_apps:
                    log_msg(f"⚠️ Daily limit reached ({max_apps})")
                    break

                platform = job.get("platform", "")
                title    = job.get("title", "")
                company  = job.get("company", "")
                url      = job.get("url", "")

                automation_state["current_job"] = f"{title} @ {company}"
                log_msg(f"→ {title} @ {company} ({platform})")

                if url and is_already_applied(url):
                    log_msg("  Skipping — already applied")
                    continue

                page    = context.new_page()
                success = False
                try:
                    if platform == "linkedin":
                        from platforms.linkedin import LinkedInPlatform
                        p = LinkedInPlatform(config, context)
                        success = p.apply_to_job(page, job, form_filler)
                    elif platform == "indeed":
                        from platforms.indeed import IndeedPlatform
                        p = IndeedPlatform(config, context)
                        success = p.apply_to_job(page, job, form_filler)
                    elif platform == "naukri":
                        from platforms.naukri import NaukriPlatform
                        p = NaukriPlatform(config, context)
                        success = p.apply_to_job(page, job, form_filler)
                    elif platform == "glassdoor":
                        from platforms.glassdoor import GlassdoorPlatform
                        p = GlassdoorPlatform(config, context)
                        success = p.apply_to_job(page, job, form_filler)

                    if success:
                        add_application(platform=platform, company=company, job_title=title,
                                        location=job.get("location",""), job_url=url)
                        applied += 1
                        automation_state["applied"] = applied
                        log_msg(f"  ✅ Applied! ({applied}/{max_apps})")
                    else:
                        add_skipped(platform, url, "apply_failed")
                        log_msg("  ❌ Could not apply")
                except Exception as e:
                    log_msg(f"  ❌ Error: {e}")
                finally:
                    page.close()

                if applied < max_apps:
                    log_msg(f"  Waiting {delay_sec}s...")
                    time.sleep(delay_sec)

            browser.close()

        log_msg(f"🏁 Session complete — Applied to {applied} jobs")
    except Exception as e:
        log_msg(f"❌ Fatal error: {e}")
    finally:
        with automation_lock:
            automation_state["running"] = False
            automation_state["current_job"] = ""


@app.route("/api/automation/start", methods=["POST"])
def start_automation():
    with automation_lock:
        if automation_state["running"]:
            return jsonify({"ok": False, "error": "Already running"})
        automation_state.update({"running": True, "log": [], "applied": 0, "found": 0, "current_job": ""})

    config = load_config()
    t = threading.Thread(target=run_automation_thread, args=(config,), daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Automation started"})

@app.route("/api/automation/stop", methods=["POST"])
def stop_automation():
    with automation_lock:
        automation_state["running"] = False
    return jsonify({"ok": True, "message": "Stop signal sent"})

@app.route("/api/automation/status")
def automation_status():
    return jsonify({
        "running":     automation_state["running"],
        "applied":     automation_state["applied"],
        "found":       automation_state["found"],
        "current_job": automation_state["current_job"],
        "started_at":  automation_state["started_at"],
        "log":         automation_state["log"][-50:],
    })

@app.route("/api/automation/log")
def automation_log():
    return jsonify({"log": automation_state["log"]})


# ─── Logs API ─────────────────────────────────────────────────────────────────

@app.route("/api/logs")
def list_logs():
    LOG_DIR.mkdir(exist_ok=True)
    files = sorted(LOG_DIR.glob("*.log"), reverse=True)
    return jsonify([{"name": f.name, "size_kb": round(f.stat().st_size/1024,1),
                     "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                    for f in files[:20]])

@app.route("/api/logs/<filename>")
def get_log(filename):
    path = LOG_DIR / filename
    if not path.exists():
        return jsonify({"error": "Not found"}), 404
    return path.read_text(errors="replace"), 200, {"Content-Type": "text/plain"}


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("🌐 Job Applier Web UI → http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)
