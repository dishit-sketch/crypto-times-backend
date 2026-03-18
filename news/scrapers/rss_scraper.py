"""
RSS feed scraper for The Crypto Times.
Only imports recent, crypto-related articles.
"""

import logging
import hashlib
import re
from datetime import datetime, timedelta, timezone as dt_tz
import feedparser
from django.utils import timezone
from django.utils.html import strip_tags

from news.models import NewsArticle, Source
from news.scrapers.crypto_filter import is_crypto_related

logger = logging.getLogger("news")

MAX_AGE_HOURS = 72


def _extract_images(entry) -> list:
    images = []

    for media in getattr(entry, "media_content", []):
        url = media.get("url", "")
        if url and any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
            images.append(url)

    for media in getattr(entry, "media_thumbnail", []):
        url = media.get("url", "")
        if url:
            images.append(url)

    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            images.append(enc.get("href", ""))

    content_html = ""
    if hasattr(entry, "content"):
        content_html = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content_html = entry.summary or ""

    if "<img" in content_html:
        for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', content_html):
            img_url = match.group(1)
            if img_url.startswith("http"):
                images.append(img_url)

    seen = set()
    clean = []
    for url in images:
        if url not in seen and url.startswith("http"):
            seen.add(url)
            clean.append(url)
    return clean[:5]


def _generate_external_id(entry, source) -> str:
    raw = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(f"{source.id}:{raw}".encode()).hexdigest()[:64]


def _get_entry_time(entry):
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, field, None) or entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=dt_tz.utc)
            except Exception:
                continue
    return None


def scrape_rss_source(source) -> list:
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

    # ── Cutoff based on last_fetched_at ──────────────────────
    # New source → only fetch last 1 hour to avoid flood of old articles
    # Existing source → fetch since last fetch time
    if source.last_fetched_at:
        cutoff = source.last_fetched_at
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=dt_tz.utc)
    else:
        cutoff = datetime.now(dt_tz.utc) - timedelta(hours=1)
        logger.info("New source '%s' — only fetching last 1 hour", source.name)

    skipped_old = 0
    skipped_noncrypto = 0
    skipped_dupe = 0

    # Load recent titles ONCE before the loop
    recent_titles = list(
        NewsArticle.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=72)
        ).values_list("title", flat=True)[:300]
    )

    for entry in feed.entries[:30]:

        # ── Time filter ──────────────────────────────────────
        entry_time = _get_entry_time(entry)
        if entry_time and entry_time < cutoff:
            skipped_old += 1
            continue

        # ── Extract title FIRST ──────────────────────────────
        title = entry.get("title", "").strip()
        if not title or len(title) < 10:
            continue

        # ── Clean Google News source suffix ──────────────────
        title = re.sub(
            r'\s*[-–|]\s*(CoinDesk|CoinTelegraph|Decrypt|Bloomberg|Reuters|Forbes|CNBC|AP News|WSJ|NYT|Blockworks|The Block|Bitcoin Magazine|Messari|Glassnode|Chainalysis|CryptoSlate|NewsBTC|AMBCrypto|Bitcoinist|Protos|Kraken).*$',
            '', title, flags=re.IGNORECASE
        ).strip()

        if not title or len(title) < 10:
            continue

        # ── External ID dedup ────────────────────────────────
        external_id = _generate_external_id(entry, source)
        if NewsArticle.objects.filter(external_id=external_id).exists():
            skipped_dupe += 1
            continue

        # ── Exact title dedup ────────────────────────────────
        if NewsArticle.objects.filter(title=title).exists():
            skipped_dupe += 1
            continue

        # ── Fuzzy title dedup ────────────────────────────────
        from difflib import SequenceMatcher
        similar = False
        for existing_title in recent_titles:
            ratio = SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
            if ratio > 0.82:
                similar = True
                break
        if similar:
            skipped_dupe += 1
            continue

        # ── Extract content ──────────────────────────────────
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

        # ── Crypto filter ────────────────────────────────────
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

        # Add to local list to prevent dupes within same fetch cycle
        recent_titles.append(title)

        logger.info("Created article: %s", title[:60])

    logger.info(
        "RSS %s: %d created, %d old, %d non-crypto, %d dupes",
        source.name, len(created), skipped_old, skipped_noncrypto, skipped_dupe,
    )

    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return created


def _detect_category(title: str) -> str:
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


def _extract_tags(entry) -> list:
    tags = []
    for tag in getattr(entry, "tags", []):
        term = tag.get("term", "").strip()
        if term and len(term) < 50:
            tags.append(term)
    return tags[:10]
