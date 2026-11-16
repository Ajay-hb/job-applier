"""
Database tracker for job applications.
Uses SQLite to store all application history.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "tracker" / "applications.db"


def init_db():
    """Initialize the SQLite database and create tables."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            platform TEXT NOT NULL,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            location TEXT,
            job_url TEXT,
            salary TEXT,
            date_applied TEXT,
            status TEXT DEFAULT 'applied',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS skipped_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            job_url TEXT,
            reason TEXT,
            skipped_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_application(platform, company, job_title, location="", job_url="", salary="", notes="", job_id=""):
    """Record a successfully submitted application."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications (job_id, platform, company, job_title, location, job_url, salary, date_applied, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, platform, company, job_title, location, job_url, salary, datetime.now().strftime("%Y-%m-%d %H:%M"), notes))
    conn.commit()
    conn.close()


def add_skipped(platform, job_url, reason):
    """Record a skipped job with the reason."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO skipped_jobs (platform, job_url, reason) VALUES (?, ?, ?)",
              (platform, job_url, reason))
    conn.commit()
    conn.close()


def is_already_applied(job_url):
    """Check if we've already applied to this job URL."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM applications WHERE job_url = ?", (job_url,))
    result = c.fetchone()
    conn.close()
    return result is not None


def update_status(job_url, status, notes=""):
    """Update the status of an application (applied/interview/rejected/offer)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE applications SET status = ?, notes = ? WHERE job_url = ?",
              (status, notes, job_url))
    conn.commit()
    conn.close()


def get_all_applications(limit=None, platform=None, status=None):
    """Fetch applications with optional filters."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {limit}"
    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def get_stats():
    """Return summary statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM applications")
    stats["total"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'applied'")
    stats["applied"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'interview'")
    stats["interviews"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'rejected'")
    stats["rejected"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'offer'")
    stats["offers"] = c.fetchone()[0]
    c.execute("SELECT platform, COUNT(*) as count FROM applications GROUP BY platform")
    stats["by_platform"] = {row[0]: row[1] for row in c.fetchall()}
    c.execute("""
        SELECT date_applied, COUNT(*) as count
        FROM applications
        GROUP BY date(date_applied)
        ORDER BY date_applied DESC
        LIMIT 7
    """)
    stats["last_7_days"] = [{"date": row[0], "count": row[1]} for row in c.fetchall()]
    conn.close()
    return stats


if __name__ == "__main__":
    init_db()
    print("✅ Database initialized at:", DB_PATH)
