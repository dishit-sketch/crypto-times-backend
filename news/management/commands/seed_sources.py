"""
Django management command to seed the database with starter sources.
Usage: python manage.py seed_sources
"""

from django.core.management.base import BaseCommand
from news.models import Source


STARTER_SOURCES = [
    {
        "name": "CoinDesk RSS",
        "type": "rss",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "description": "Leading crypto news outlet covering Bitcoin, Ethereum, and blockchain.",
        "reliability_score": 90,
    },
    {
        "name": "CoinTelegraph RSS",
        "type": "rss",
        "url": "https://cointelegraph.com/rss",
        "description": "Major crypto and blockchain technology publication.",
        "reliability_score": 85,
    },
    {
        "name": "Bitcoin Magazine RSS",
        "type": "rss",
        "url": "https://bitcoinmagazine.com/.rss/full/",
        "description": "The oldest publication covering Bitcoin news and analysis.",
        "reliability_score": 92,
    },
    {
        "name": "Decrypt RSS",
        "type": "rss",
        "url": "https://decrypt.co/feed",
        "description": "Web3 media company delivering demystified crypto news.",
        "reliability_score": 87,
    },
    {
        "name": "The Block",
        "type": "website",
        "url": "https://www.theblock.co",
        "description": "Research-driven crypto journalism with in-depth analysis.",
        "reliability_score": 88,
    },
    {
        "name": "@VitalikButerin",
        "type": "twitter",
        "url": "https://x.com/VitalikButerin",
        "description": "Ethereum co-founder. Frequent insights on crypto and tech.",
        "reliability_score": 93,
    },
    {
        "name": "@saborbank",
        "type": "twitter",
        "url": "https://x.com/saborbank",
        "description": "On-chain analyst specializing in whale movements.",
        "reliability_score": 75,
    },
]


class Command(BaseCommand):
    help = "Seed the database with starter news sources."

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
                self.stdout.write(f"  ○ {data['name']} (already exists)")

        self.stdout.write(self.style.SUCCESS(f"\nDone — {created_count} new sources added."))
