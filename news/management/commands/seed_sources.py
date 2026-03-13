"""
Seed 100+ original crypto news sources for CryptoTimes.io.
Usage: python manage.py seed_sources
Also auto-runs on first server startup via apps.py
"""

from django.core.management.base import BaseCommand
from news.models import Source
from news.sources_list import STARTER_SOURCES


class Command(BaseCommand):
    help = "Seed the database with 100+ original crypto news sources."

    def handle(self, *args, **options):
        created_count = 0
        for data in STARTER_SOURCES:
            _, created = Source.objects.get_or_create(
                url=data["url"],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(f"  + {data['name']}")
            else:
                self.stdout.write(f"  . {data['name']} (exists)")

        total = Source.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {created_count} new sources added. Total: {total} sources."
        ))
