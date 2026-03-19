"""
X (Twitter) scraper for The Crypto Times.

Uses Twitter API v2 with Bearer Token to monitor crypto accounts
and create news articles from their tweets in real-time.

Monitored accounts include exchanges, foundations, analysts,
security firms, and regulatory bodies.
"""

import logging
import hashlib
import re
import time
from datetime import datetime, timedelta, timezone as dt_tz

import httpx
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

from news.models import NewsArticle, Source
from news.scrapers.crypto_filter import is_crypto_related

logger = logging.getLogger("news")

# ── Twitter API v2 base URL ─────────────────────────────────
TWITTER_API_BASE = "https://api.twitter.com/2"

# ── Accounts to monitor (username → display name) ───────────
# Add or remove accounts as needed
CRYPTO_ACCOUNTS = {
    "whale_alert": "Whale Alert",
    "binance": "Binance",
    "coinaboreta": "Coinbase",
    "kaboraten": "Kraken",
    "WatcherGuru": "Watcher Guru",
    "caborez_binance": "CZ Binance",
    "VitalikButerin": "Vitalik Buterin",
    "saylor": "Michael Saylor",
    "SECGov": "SEC",
    "tier10k": "Tier10K",
    "BitcoinMagazine": "Bitcoin Magazine",
    "Cointelegraph": "CoinTelegraph",
    "Decrypt": "Decrypt",
    "BlockworksRes": "Blockworks",
    "PeckShieldAlert": "PeckShield",
    "SlowMist_Team": "SlowMist",
    "zachxbt": "ZachXBT",
    "lookonchain": "Lookonchain",
    "ArkhamIntel": "Arkham Intelligence",
    "RippleXDev": "Ripple",
}

# ── Minimum tweet length to consider as news ────────────────
MIN_TWEET_LENGTH = 30

# ── Rate limit: max accounts to fetch per cycle ─────────────
# Twitter free tier: 15 requests per 15 minutes
MAX_ACCOUNTS_PER_CYCLE = 12
DELAY_BETWEEN_REQUESTS = 5  # seconds


def _get_headers() -> dict:
    """Build authorization headers for Twitter API v2."""
    token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_user_id(username: str, headers: dict) -> str | None:
    """
    Get Twitter user ID from username.
    Returns None if user not found or API fails.
    """
    try:
        response = httpx.get(
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            headers=headers,
            timeout=15,
        )

        if response.status_code == 429:
            logger.warning("Twitter rate limited on user lookup: %s", username)
            return None

        if response.status_code != 200:
            logger.warning(
                "Twitter user lookup failed for @%s: HTTP %d",
                username, response.status_code,
            )
            return None

        data = response.json()
        user_data = data.get("data", {})
        return user_data.get("id")

    except Exception as e:
        logger.error("Twitter user lookup error for @%s: %s", username, str(e)[:60])
        return None


def _get_user_tweets(
    user_id: str,
    username: str,
    headers: dict,
    since_time: str | None = None,
) -> list[dict]:
    """
    Fetch recent tweets from a user.
    Returns list of tweet dicts with text, id, created_at, images.
    """
    params = {
        "max_results": 10,
        "tweet.fields": "created_at,text,attachments,entities,public_metrics",
        "expansions": "attachments.media_keys",
        "media.fields": "url,preview_image_url,type",
    }

    if since_time:
        params["start_time"] = since_time

    try:
        response = httpx.get(
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            headers=headers,
            params=params,
            timeout=15,
        )

        if response.status_code == 429:
            logger.warning("Twitter rate limited on tweets for @%s", username)
            return []

        if response.status_code != 200:
            logger.warning(
                "Twitter tweets fetch failed for @%s: HTTP %d",
                username, response.status_code,
            )
            return []

        data = response.json()
        tweets = data.get("data", [])

        # Extract media URLs from includes
        media_map = {}
        includes = data.get("includes", {})
        for media in includes.get("media", []):
            media_key = media.get("media_key", "")
            url = media.get("url") or media.get("preview_image_url", "")
            if media_key and url:
                media_map[media_key] = url

        # Attach images to tweets
        results = []
        for tweet in tweets:
            tweet_images = []
            attachments = tweet.get("attachments", {})
            for key in attachments.get("media_keys", []):
                if key in media_map:
                    tweet_images.append(media_map[key])

            results.append({
                "id": tweet.get("id", ""),
                "text": tweet.get("text", ""),
                "created_at": tweet.get("created_at", ""),
                "images": tweet_images,
                "metrics": tweet.get("public_metrics", {}),
                "username": username,
            })

        return results

    except Exception as e:
        logger.error("Twitter tweets fetch error for @%s: %s", username, str(e)[:60])
        return []


def _clean_tweet_text(text: str) -> str:
    """Remove URLs and clean tweet text for title/summary."""
    # Remove t.co URLs
    cleaned = re.sub(r"https?://t\.co/\S+", "", text).strip()
    # Remove multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_retweet(text: str) -> bool:
    """Check if tweet is a retweet (starts with RT @)."""
    return text.strip().startswith("RT @")


def _is_reply(text: str) -> bool:
    """Check if tweet is a reply (starts with @username)."""
    return text.strip().startswith("@")


def _tweet_to_article(
    tweet: dict,
    source: Source,
    display_name: str,
) -> NewsArticle | None:
    """
    Convert a tweet dict to a NewsArticle.
    Returns None if tweet is not newsworthy or is a duplicate.
    """
    tweet_id = tweet.get("id", "")
    raw_text = tweet.get("text", "")
    username = tweet.get("username", "")
    images = tweet.get("images", [])
    metrics = tweet.get("metrics", {})

    if not raw_text or len(raw_text) < MIN_TWEET_LENGTH:
        return None

    # Skip retweets and replies
    if _is_retweet(raw_text) or _is_reply(raw_text):
        return None

    # Clean text for title
    clean_text = _clean_tweet_text(raw_text)
    if not clean_text or len(clean_text) < 20:
        return None

    # Check crypto relevance
    if not is_crypto_related(clean_text, clean_text):
        logger.debug("Tweet from @%s not crypto related, skipping", username)
        return None

    # Generate unique external_id
    external_id = hashlib.sha256(
        f"{source.id}:tweet:{tweet_id}".encode()
    ).hexdigest()[:64]

    # Check for duplicates
    if NewsArticle.objects.filter(external_id=external_id).exists():
        return None

    # Also check fuzzy title duplicate
    title = clean_text[:120] + ("…" if len(clean_text) > 120 else "")
    if NewsArticle.objects.filter(title=title).exists():
        return None

    # Create article
    tweet_url = f"https://x.com/{username}/status/{tweet_id}"

    # Add engagement info if significant
    likes = metrics.get("like_count", 0)
    retweets = metrics.get("retweet_count", 0)
    engagement_note = ""
    if likes > 100 or retweets > 50:
        engagement_note = f" (Engagement: {likes:,} likes, {retweets:,} retweets)"

    summary = clean_text[:300]
    content = f"<p>{clean_text}{engagement_note}</p>"

    article = NewsArticle.objects.create(
        title=title,
        summary=summary,
        content=content,
        source=source,
        original_url=tweet_url,
        images=images,
        external_id=external_id,
        status="pending",
    )

    logger.info(
        "Created tweet article: @%s — %s",
        username, title[:50],
    )

    return article


def scrape_twitter_source(source: Source) -> list[NewsArticle]:
    """
    Fetch recent tweets from a Twitter/X source.

    The source.url should be one of:
    - A Twitter profile URL like https://x.com/whale_alert
    - A username like whale_alert
    - The special keyword "ALL" to monitor all CRYPTO_ACCOUNTS

    Returns list of newly created NewsArticle objects.
    """
    token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
    if not token:
        logger.warning(
            "TWITTER_BEARER_TOKEN not set — skipping Twitter source '%s'",
            source.name,
        )
        source.last_fetched_at = timezone.now()
        source.save(update_fields=["last_fetched_at"])
        return []

    headers = _get_headers()
    created_articles = []

    # Determine which accounts to scrape
    url = source.url.strip().rstrip("/")

    if url.upper() == "ALL":
        # Monitor all configured crypto accounts
        accounts_to_check = dict(
            list(CRYPTO_ACCOUNTS.items())[:MAX_ACCOUNTS_PER_CYCLE]
        )
    elif "x.com/" in url or "twitter.com/" in url:
        # Single account from URL
        username = url.split("/")[-1].lstrip("@")
        display_name = CRYPTO_ACCOUNTS.get(username, username)
        accounts_to_check = {username: display_name}
    else:
        # Assume it's a plain username
        username = url.lstrip("@")
        display_name = CRYPTO_ACCOUNTS.get(username, username)
        accounts_to_check = {username: display_name}

    # Calculate since_time — only fetch tweets since last fetch
    if source.last_fetched_at:
        since_time = source.last_fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # First run — only get tweets from last 30 minutes
        since_time = (
            datetime.now(dt_tz.utc) - timedelta(minutes=30)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(
        "Twitter: checking %d accounts since %s",
        len(accounts_to_check), since_time,
    )

    for username, display_name in accounts_to_check.items():
        # Get user ID
        user_id = _get_user_id(username, headers)
        if not user_id:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue

        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Get tweets
        tweets = _get_user_tweets(user_id, username, headers, since_time)
        if not tweets:
            continue

        logger.info(
            "Twitter @%s: found %d tweets",
            username, len(tweets),
        )

        for tweet in tweets:
            article = _tweet_to_article(tweet, source, display_name)
            if article:
                created_articles.append(article)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Update last_fetched_at
    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    logger.info(
        "Twitter fetch complete: %d new articles from %d accounts",
        len(created_articles), len(accounts_to_check),
    )

    return created_articles
