"""
X (Twitter) scraper for The Crypto Times.

NOTE: Twitter's API requires authentication and an approved developer account.
This module provides the structure — you must supply your own API keys via
the Twitter API v2 or a library like tweepy.

For production, consider using:
  - Twitter API v2 (official)
  - Nitter instances (unofficial, may break)
  - Third-party aggregation services
"""

import logging
import hashlib
from django.utils import timezone

from news.models import NewsArticle, Source

logger = logging.getLogger("news")


def scrape_twitter_source(source: Source) -> list[NewsArticle]:
    """
    Fetch recent tweets from a Twitter/X source.

    This is a structured placeholder. To make it functional, integrate
    the Twitter API v2 or tweepy library.
    """
    logger.info(
        "Twitter scraping for '%s' — requires API integration. "
        "Set up Twitter API v2 credentials to enable.",
        source.name,
    )

    # ── Integration point ───────────────────────────────────
    # To enable real Twitter scraping, uncomment and configure:
    #
    # import tweepy
    #
    # client = tweepy.Client(bearer_token=settings.TWITTER_BEARER_TOKEN)
    # username = source.url.rstrip("/").split("/")[-1]
    # user = client.get_user(username=username)
    # tweets = client.get_users_tweets(
    #     user.data.id,
    #     max_results=10,
    #     tweet_fields=["created_at", "text", "attachments"],
    #     expansions=["attachments.media_keys"],
    #     media_fields=["url", "preview_image_url"],
    # )
    #
    # For each tweet, create a NewsArticle:
    #   - title: First 100 chars of tweet
    #   - content: Full tweet text
    #   - images: Attached media URLs
    #   - external_id: Tweet ID

    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return []


def _tweet_to_article(tweet_data: dict, source: Source) -> NewsArticle | None:
    """Convert a tweet dict to a NewsArticle (helper for when API is connected)."""
    tweet_id = tweet_data.get("id", "")
    text = tweet_data.get("text", "")

    if not text:
        return None

    external_id = hashlib.sha256(f"{source.id}:tweet:{tweet_id}".encode()).hexdigest()[:64]

    if NewsArticle.objects.filter(external_id=external_id).exists():
        return None

    title = text[:100] + ("…" if len(text) > 100 else "")
    images = tweet_data.get("images", [])

    article = NewsArticle.objects.create(
        title=title,
        summary=text[:300],
        content=f"<p>{text}</p>",
        source=source,
        original_url=f"https://x.com/i/status/{tweet_id}",
        images=images,
        external_id=external_id,
    )
    return article
