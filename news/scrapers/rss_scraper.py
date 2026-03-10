"""
RSS feed scraper for The Crypto Times.
Parses RSS/Atom feeds and creates NewsArticle entries.
"""

import logging
import hashlib
import feedparser
from django.utils import timezone
from django.utils.html import strip_tags

from news.models import NewsArticle, Source

logger = logging.getLogger("news")


def _extract_images(entry) -> list[str]:
    """Extract image URLs from a feed entry."""
    images = []

    # Check media_content
    for media in getattr(entry, "media_content", []):
        url = media.get("url", "")
        if url and any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
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

    return list(dict.fromkeys(images))[:5]  # Dedupe, max 5


def _generate_external_id(entry, source: Source) -> str:
    """Generate a unique ID for deduplication."""
    raw = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(f"{source.id}:{raw}".encode()).hexdigest()[:64]


def scrape_rss_source(source: Source) -> list[NewsArticle]:
    """Fetch and parse an RSS feed, creating articles for new entries."""
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

    for entry in feed.entries[:20]:  # Process latest 20
        external_id = _generate_external_id(entry, source)

        # Skip duplicates
        if NewsArticle.objects.filter(external_id=external_id).exists():
            continue

        title = entry.get("title", "Untitled")

        # Extract content
        content_html = ""
        if hasattr(entry, "content") and entry.content:
            content_html = entry.content[0].get("value", "")
        elif hasattr(entry, "summary_detail"):
            content_html = entry.summary_detail.get("value", "")
        elif hasattr(entry, "summary"):
            content_html = entry.summary or ""

        summary = strip_tags(content_html)[:300].strip()
        if not summary:
            summary = strip_tags(entry.get("summary", ""))[:300].strip()

        images = _extract_images(entry)

        article = NewsArticle.objects.create(
            title=title,
            summary=summary or title,
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

    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return created


def _detect_category(title: str) -> str:
    """Simple keyword-based category detection."""
    title_lower = title.lower()
    categories = {
        "DeFi": ["defi", "dex", "lending", "yield", "liquidity", "aave", "uniswap"],
        "Markets": ["price", "surge", "crash", "rally", "market", "trading", "etf", "bull", "bear"],
        "Regulation": ["sec", "regulation", "law", "compliance", "ban", "legal", "court"],
        "Technology": ["layer 2", "l2", "upgrade", "fork", "protocol", "blockchain", "scaling"],
        "NFT": ["nft", "opensea", "collectible", "token"],
        "Security": ["hack", "exploit", "scam", "phishing", "breach", "vulnerability"],
        "CBDC": ["cbdc", "central bank digital", "digital dollar", "digital euro"],
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
        if term:
            tags.append(term)
    return tags[:10]
