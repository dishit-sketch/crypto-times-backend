"""
Django management command to seed original news sources.
These are primary sources — not competitors like CoinDesk or CoinTelegraph.
Usage: python manage.py seed_sources
"""

from django.core.management.base import BaseCommand
from news.models import Source


STARTER_SOURCES = [
    # ── Official Government / Regulatory ────────────────────
    {
        "name": "SEC Press Releases RSS",
        "type": "rss",
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "description": "Official SEC press releases — crypto enforcement, ETF approvals, regulatory actions.",
        "reliability_score": 98,
    },
    {
        "name": "Federal Reserve RSS",
        "type": "rss",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "description": "Federal Reserve press releases — interest rates, CBDC updates, monetary policy.",
        "reliability_score": 99,
    },

    # ── Official Blockchain / Protocol Sources ──────────────
    {
        "name": "Ethereum Foundation Blog",
        "type": "rss",
        "url": "https://blog.ethereum.org/feed.xml",
        "description": "Official Ethereum Foundation blog — protocol upgrades, research, ecosystem updates.",
        "reliability_score": 97,
    },
    {
        "name": "Solana News RSS",
        "type": "rss",
        "url": "https://solana.com/news/rss.xml",
        "description": "Official Solana news — network updates, ecosystem growth, technical developments.",
        "reliability_score": 95,
    },

    # ── Major Exchange / Company Blogs ──────────────────────
    {
        "name": "Coinbase Blog",
        "type": "rss",
        "url": "https://www.coinbase.com/blog/rss",
        "description": "Official Coinbase blog — product launches, market insights, regulatory updates.",
        "reliability_score": 90,
    },
    {
        "name": "Binance Blog",
        "type": "rss",
        "url": "https://www.binance.com/en/feed/rss",
        "description": "Official Binance blog — exchange updates, listings, security alerts.",
        "reliability_score": 85,
    },

    # ── On-Chain Data / Analytics ───────────────────────────
    {
        "name": "Glassnode Insights",
        "type": "rss",
        "url": "https://insights.glassnode.com/rss/",
        "description": "On-chain data analysis — Bitcoin and Ethereum market intelligence.",
        "reliability_score": 92,
    },
    {
        "name": "Chainalysis Blog",
        "type": "rss",
        "url": "https://blog.chainalysis.com/feed/",
        "description": "Blockchain analytics — crime reports, compliance trends, market research.",
        "reliability_score": 93,
    },

    # ── Wire Services (original reporting) ──────────────────
    {
        "name": "Reuters Crypto RSS",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+ethereum+site:reuters.com&hl=en-US&gl=US&ceid=US:en",
        "description": "Reuters crypto coverage via Google News — original wire reporting.",
        "reliability_score": 96,
    },
    {
        "name": "Bloomberg Crypto RSS",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+blockchain+site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
        "description": "Bloomberg crypto coverage via Google News — financial market reporting.",
        "reliability_score": 95,
    },
    {
        "name": "AP News Crypto RSS",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+blockchain+site:apnews.com&hl=en-US&gl=US&ceid=US:en",
        "description": "Associated Press crypto coverage — trusted wire service reporting.",
        "reliability_score": 97,
    },

    # ── Google News Crypto Feed (aggregated original sources)
    {
        "name": "Google News Crypto",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=cryptocurrency+bitcoin+ethereum&hl=en-US&gl=US&ceid=US:en",
        "description": "Google News aggregation — top crypto stories from original sources worldwide.",
        "reliability_score": 80,
    },

    # ── GitHub / Technical Sources ──────────────────────────
    {
        "name": "Bitcoin Core Releases",
        "type": "rss",
        "url": "https://github.com/bitcoin/bitcoin/releases.atom",
        "description": "Official Bitcoin Core software releases — protocol changes and updates.",
        "reliability_score": 99,
    },
]


class Command(BaseCommand):
    help = "Seed the database with original news sources (not competitors)."

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
