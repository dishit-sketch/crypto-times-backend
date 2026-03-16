"""
RSS feed scraper for The Crypto Times.
Only imports recent, crypto-related articles.
"""

import logging
import hashlib
from datetime import datetime, timedelta, timezone as dt_tz
import feedparser
from django.utils import timezone
from django.utils.html import strip_tags

from news.models import NewsArticle, Source
from news.scrapers.crypto_filter import is_crypto_related

logger = logging.getLogger("news")

# Only fetch articles from the last N hours
MAX_AGE_HOURS = 48


def _extract_images(entry) -> list[str]:
    """Extract image URLs from a feed entry."""
    images = []

    # Check media_content
    for media in getattr(entry, "media_content", []):
        url = media.get("url", "")
        if url and any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
            images.append(url)

    # Check media_thumbnail
    for media in getattr(entry, "media_thumbnail", []):
        url = media.get("url", "")
        if url:
            images.append(url)

    # Check enclosures
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            images.append(enc.get("href", ""))

    # Check for <img> tags in content
    content_html = ""
    if hasattr(entry, "content"):
        content_html = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content_html = entry.summary or ""

    if "<img" in content_html:
        import re
        for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content_html):
            img_url = match.group(1)
            if img_url.startswith("http"):
                images.append(img_url)

    # Dedupe and filter
    seen = set()
    clean = []
    for url in images:
        if url not in seen and url.startswith("http"):
            seen.add(url)
            clean.append(url)
    return clean[:5]


def _generate_external_id(entry, source: Source) -> str:
    """Generate a unique ID for deduplication."""
    raw = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(f"{source.id}:{raw}".encode()).hexdigest()[:64]


def _get_entry_time(entry) -> datetime | None:
    """Try to extract publish time from feed entry."""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, field, None) or entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=dt_tz.utc)
            except Exception:
                continue
    return None


def scrape_rss_source(source: Source) -> list[NewsArticle]:
    """Fetch and parse an RSS feed, creating articles for new crypto entries only."""
    logger.info("Scraping RSS: %s (%s)", source.name, source.url)
    created = []

    try:
        feed = feedparser.parse(source.url)
    except Exception as e:
        logger.error("Failed to parse feed %s: %s", source.url, e)
        return created

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s returned errors: %s", source.url, feed.bozo_exception)
        return created

    cutoff = datetime.now(dt_tz.utc) - timedelta(hours=MAX_AGE_HOURS)
    skipped_old = 0
    skipped_noncrypto = 0
    skipped_dupe = 0

    for entry in feed.entries[:30]:  # Check latest 30
        # ── Time filter — skip old articles ─────────────────
        entry_time = _get_entry_time(entry)
        if entry_time and entry_time < cutoff:
            skipped_old += 1
            continue

        # ── Dedup filter ────────────────────────────────────
        external_id = _generate_external_id(entry, source)
        if NewsArticle.objects.filter(external_id=external_id).exists():
            skipped_dupe += 1
            continue
         # Fuzzy title match — skip if 80% similar title exists
        from difflib import SequenceMatcher
        similar = False
        recent_titles = NewsArticle.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=48)
        ).values_list("title", flat=True)[:200]
        for existing_title in recent_titles:
            ratio = SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
            if ratio > 0.8:
                similar = True
                break
        if similar:
            skipped_dupe += 1
            continue

        # Also check title dedup across all sources
        if NewsArticle.objects.filter(title=title.strip()).exists():
            skipped_dupe += 1
            continue

        title = entry.get("title", "").strip()
        if not title or len(title) < 10:
            continue

        # Extract summary for filtering
        content_html = ""
        if hasattr(entry, "content") and entry.content:
            content_html = entry.content[0].get("value", "")
        elif hasattr(entry, "summary_detail"):
            content_html = entry.summary_detail.get("value", "")
        elif hasattr(entry, "summary"):
            content_html = entry.summary or ""

        summary = strip_tags(content_html)[:500].strip()
        if not summary:
            summary = strip_tags(entry.get("summary", ""))[:500].strip()

        # ── Crypto filter — skip non-crypto articles ────────
        if not is_crypto_related(title, summary):
            skipped_noncrypto += 1
            continue

        images = _extract_images(entry)

        article = NewsArticle.objects.create(
            title=title,
            summary=(summary or title)[:300],
            content=content_html or f"<p>{summary}</p>",
            source=source,
            original_url=entry.get("link", ""),
            author=entry.get("author", ""),
            images=images,
            external_id=external_id,
            category=_detect_category(title),
            tags=_extract_tags(entry),
        )
        created.append(article)
        logger.info("Created article: %s", title[:60])

    logger.info(
        "RSS %s: %d created, %d old, %d non-crypto, %d dupes",
        source.name, len(created), skipped_old, skipped_noncrypto, skipped_dupe,
    )

    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return created


def _detect_category(title: str) -> str:
    """Keyword-based category detection."""
    title_lower = title.lower()
    categories = {
        "DeFi": ["defi", "dex", "lending", "yield", "liquidity", "aave", "uniswap", "compound", "tvl"],
        "Markets": ["price", "surge", "crash", "rally", "market", "trading", "etf", "bull", "bear", "ath", "whale"],
        "Regulation": ["sec", "regulation", "law", "compliance", "ban", "legal", "court", "cftc", "lawsuit"],
        "Technology": ["layer 2", "l2", "upgrade", "fork", "protocol", "blockchain", "scaling", "rollup", "zk"],
        "NFT": ["nft", "opensea", "collectible"],
        "Security": ["hack", "exploit", "scam", "phishing", "breach", "vulnerability", "rug pull", "stolen"],
        "CBDC": ["cbdc", "central bank digital", "digital dollar", "digital euro", "digital yuan"],
    }
    for cat, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            return cat
    return "General"


def _extract_tags(entry) -> list[str]:
    """Extract tags from feed entry."""
    tags = []
    for tag in getattr(entry, "tags", []):
        term = tag.get("term", "").strip()
        if term and len(term) < 50:
            tags.append(term)
    return tags[:10]
