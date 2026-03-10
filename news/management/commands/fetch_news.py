"""
Django management command to fetch news from all sources.
Usage: python manage.py fetch_news
"""

from django.core.management.base import BaseCommand
from news.scrapers.orchestrator import fetch_all_sources


class Command(BaseCommand):
    help = "Fetch news from all active sources, verify with AI, and ensure images."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting news fetch..."))
        count = fetch_all_sources()
        self.stdout.write(self.style.SUCCESS(f"Done — {count} new articles created."))
