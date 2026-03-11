"""
Auto-starting background scheduler.
Fetches news from all active sources every N minutes.
Starts automatically when Django boots up.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings

logger = logging.getLogger("news")

scheduler = BackgroundScheduler()
_started = False


def start():
    global _started
    if _started:
        return
    _started = True

    from news.scrapers.orchestrator import fetch_all_sources

    interval = getattr(settings, "FETCH_INTERVAL_MINUTES", 5)

    scheduler.add_job(
        fetch_all_sources,
        trigger=IntervalTrigger(minutes=interval),
        id="fetch_news_auto",
        name=f"Auto-fetch news every {interval} minutes",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started — fetching every %d minutes", interval)
