"""
main.py — Job Applier Orchestrator
Entry point for the automatic job application system.
"""

import sys
import time
import logging
import yaml
import schedule
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tracker.db import init_db, add_application, add_skipped, is_already_applied, get_stats
from agents.scraper import JobScraper
from agents.form_filler import FormFiller

console = Console()

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    if not config_path.exists():
        console.print("[red]❌ config/settings.yaml not found![/red]")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def print_banner():
    console.print(Panel.fit(
        "[bold blue]🤖 Auto Job Applier[/bold blue]\n"
        "[dim]Multi-platform automated job application bot[/dim]",
        border_style="blue"
    ))


def print_stats():
    stats = get_stats()
    table = Table(title="📊 Application Stats", border_style="dim")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold white")
    table.add_row("Total Applied", str(stats["total"]))
    table.add_row("Interviews", str(stats["interviews"]))
    table.add_row("Rejected", str(stats["rejected"]))
    table.add_row("Offers 🎉", str(stats["offers"]))
    for platform, count in stats.get("by_platform", {}).items():
        table.add_row(f"  └ {platform.capitalize()}", str(count))
    console.print(table)


def run_session(config: dict):
    """Main automation session."""
    from playwright.sync_api import sync_playwright

    automation = config.get("automation", {})
    max_apps = automation.get("max_daily_applications", 50)
    delay_between = automation.get("delay_between_apps", 30)
    headless = automation.get("headless", False)
    slow_mo = automation.get("slow_mo", 500)

    applied_count = 0

    console.rule("[bold]Starting Job Search Session[/bold]")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        scraper = JobScraper(config, context)
        form_filler = FormFiller(config)

        # 1. Scrape jobs from all platforms
        console.print("\n[yellow]🔍 Searching for jobs...[/yellow]")
        jobs = scraper.scrape_all()
        console.print(f"[green]Found {len(jobs)} unique jobs[/green]")

        if not jobs:
            console.print("[red]No jobs found. Check your config keywords and credentials.[/red]")
            browser.close()
            return

        # 2. Apply to each job
        console.rule("[bold]Applying to Jobs[/bold]")
        for job in jobs:
            if applied_count >= max_apps:
                console.print(f"[yellow]⚠️  Daily limit reached ({max_apps} applications)[/yellow]")
                break

            platform = job.get("platform", "unknown")
            title = job.get("title", "Unknown Role")
            company = job.get("company", "Unknown Company")
            url = job.get("url", "")

            console.print(f"\n[dim]→[/dim] [bold]{title}[/bold] @ [cyan]{company}[/cyan] [dim]({platform})[/dim]")

            # Skip already applied
            if url and is_already_applied(url):
                console.print("  [dim]Skipping — already applied[/dim]")
                add_skipped(platform, url, "already_applied")
                continue

            # Apply based on platform
            page = context.new_page()
            try:
                success = False
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
                    add_application(
                        platform=platform,
                        company=company,
                        job_title=title,
                        location=job.get("location", ""),
                        job_url=url,
                        job_id=job.get("job_id", ""),
                    )
                    applied_count += 1
                    console.print(f"  [green]✅ Applied! ({applied_count}/{max_apps})[/green]")
                else:
                    add_skipped(platform, url, "apply_failed")
                    console.print("  [red]❌ Could not apply[/red]")

                # Screenshot on error if configured
                if not success and automation.get("screenshot_on_error"):
                    ss_path = log_dir / f"error_{platform}_{datetime.now().strftime('%H%M%S')}.png"
                    page.screenshot(path=str(ss_path))

            except Exception as e:
                logger.error(f"Error applying to {url}: {e}")
                console.print(f"  [red]❌ Error: {e}[/red]")
            finally:
                page.close()

            # Human-like delay between applications
            if applied_count < max_apps:
                console.print(f"  [dim]Waiting {delay_between}s...[/dim]")
                time.sleep(delay_between)

        browser.close()

    console.rule("[bold]Session Complete[/bold]")
    console.print(f"[bold green]✅ Applied to {applied_count} jobs this session[/bold green]")
    print_stats()


def main():
    print_banner()
    init_db()
    config = load_config()

    # Check command-line args
    if len(sys.argv) > 1:
        if sys.argv[1] == "dashboard":
            console.print("[blue]🌐 Starting dashboard at http://localhost:5000[/blue]")
            from dashboard.app import app
            app.run(debug=False, port=5000)
            return
        elif sys.argv[1] == "stats":
            print_stats()
            return
        elif sys.argv[1] == "run":
            run_session(config)
            return

    # Interactive menu
    console.print("\n[bold]What would you like to do?[/bold]")
    console.print("  [cyan]1[/cyan] — Run job application session now")
    console.print("  [cyan]2[/cyan] — Open dashboard (http://localhost:5000)")
    console.print("  [cyan]3[/cyan] — Show stats")
    console.print("  [cyan]4[/cyan] — Schedule daily runs")
    console.print("  [cyan]q[/cyan] — Quit\n")

    choice = input("Enter choice: ").strip()

    if choice == "1":
        run_session(config)
    elif choice == "2":
        console.print("[blue]🌐 Starting dashboard at http://localhost:5000[/blue]")
        from dashboard.app import app
        app.run(debug=False, port=5000)
    elif choice == "3":
        print_stats()
    elif choice == "4":
        scheduler_cfg = config.get("scheduler", {})
        run_at = scheduler_cfg.get("run_at", "09:00")
        console.print(f"[yellow]⏰ Scheduled to run daily at {run_at}[/yellow]")
        schedule.every().day.at(run_at).do(run_session, config=config)
        console.print("[dim]Press Ctrl+C to stop scheduler[/dim]")
        while True:
            schedule.run_pending()
            time.sleep(60)
    elif choice == "q":
        console.print("Goodbye! 👋")
    else:
        console.print("[red]Invalid choice[/red]")


if __name__ == "__main__":
    main()
