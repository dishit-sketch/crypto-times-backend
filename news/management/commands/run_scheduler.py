"""
Django management command to start the APScheduler background scheduler.
Usage: python manage.py run_scheduler
"""

import signal
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from news.scrapers.orchestrator import fetch_all_sources


class Command(BaseCommand):
    help = "Start the background scheduler that fetches news every N minutes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=None,
            help="Override fetch interval in minutes (default: from settings).",
        )

    def handle(self, *args, **options):
        interval = options["interval"] or settings.FETCH_INTERVAL_MINUTES

        scheduler = BlockingScheduler()
        scheduler.add_job(
            fetch_all_sources,
            trigger=IntervalTrigger(minutes=interval),
            id="fetch_news",
            name=f"Fetch crypto news every {interval} minutes",
            replace_existing=True,
        )

        def shutdown(signum, frame):
            self.stdout.write(self.style.WARNING("\nShutting down scheduler..."))
            scheduler.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        self.stdout.write(
            self.style.SUCCESS(f"Scheduler started — fetching every {interval} minutes.")
        )
        self.stdout.write("Press Ctrl+C to stop.\n")

        # Run once immediately on start
        self.stdout.write(self.style.NOTICE("Running initial fetch..."))
        try:
            count = fetch_all_sources()
            self.stdout.write(self.style.SUCCESS(f"Initial fetch: {count} articles.\n"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Initial fetch error: {e}\n"))

        scheduler.start()
