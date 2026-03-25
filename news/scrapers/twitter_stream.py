"""
Twitter Filtered Stream for The Crypto Times.

Uses Twitter API v2 Filtered Stream (X Basic plan) to receive ALL tweets
from all monitored accounts in real-time via a single persistent connection.
No polling — tweets arrive within 2-3 seconds of posting.

Rules are built from active Twitter sources in the database and refreshed
every RULES_REFRESH_INTERVAL seconds (or on reconnect when the list changes).

The stream runs in a daemon background thread started on server boot.
"""

import hashlib
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from django.conf import settings

from news.scrapers.crypto_filter import is_crypto_related

logger = logging.getLogger("news")

TWITTER_API_BASE = "https://api.twitter.com/2"
MIN_TWEET_LENGTH = 30
RULES_REFRESH_INTERVAL = 300   # seconds — check for DB source changes
RECONNECT_DELAY_BASE = 5       # seconds — initial backoff on disconnect
RECONNECT_DELAY_MAX = 300      # seconds — cap backoff at 5 minutes
MAX_VERIFY_WORKERS = 3         # concurrent AI verifications

_stream_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None
_executor = ThreadPoolExecutor(max_workers=MAX_VERIFY_WORKERS, thread_name_prefix="tw-verify")


# ── Helpers ──────────────────────────────────────────────────

def _extract_username(url: str) -> str:
    url = url.strip().rstrip("/")
    m = re.search(r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    return url.lstrip("@")


def _get_headers() -> dict:
    token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _stream_headers(base: dict) -> dict:
    """Strip Content-Type for GET stream requests."""
    return {k: v for k, v in base.items() if k != "Content-Type"}


# ── Database source loading ───────────────────────────────────

def _load_usernames_from_db() -> set[str]:
    """Return lowercase usernames of all active Twitter sources."""
    from news.models import Source
    usernames: set[str] = set()
    for src in Source.objects.filter(source_type="twitter", is_active=True):
        raw = (src.url or "").strip()
        if raw.upper() == "ALL":
            continue
        u = _extract_username(raw)
        if u:
            usernames.add(u.lower())
    return usernames


# ── Rule management ───────────────────────────────────────────

def _build_rules(usernames: set[str]) -> list[str]:
    """
    Pack usernames into `from:u1 OR from:u2 ...` rule strings,
    each at most 512 characters (X Basic plan limit).
    """
    if not usernames:
        return []

    rules: list[str] = []
    parts: list[str] = []
    length = 0

    for username in sorted(usernames):
        part = f"from:{username}"
        added = len(part) + (4 if parts else 0)  # 4 = len(" OR ")
        if length + added > 512:
            rules.append(" OR ".join(parts))
            parts = [part]
            length = len(part)
        else:
            parts.append(part)
            length += added

    if parts:
        rules.append(" OR ".join(parts))

    return rules


def _get_current_rules(headers: dict) -> list[dict]:
    try:
        r = httpx.get(
            f"{TWITTER_API_BASE}/tweets/search/stream/rules",
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("data") or []
        logger.error("Get rules failed: HTTP %d — %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Get rules error: %s", e)
    return []


def _delete_rules(headers: dict, existing: list[dict]) -> bool:
    if not existing:
        return True
    ids = [rule["id"] for rule in existing]
    try:
        r = httpx.post(
            f"{TWITTER_API_BASE}/tweets/search/stream/rules",
            headers=headers,
            json={"delete": {"ids": ids}},
            timeout=15,
        )
        if r.status_code == 200:
            return True
        logger.error("Delete rules failed: HTTP %d — %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Delete rules error: %s", e)
    return False


def _add_rules(headers: dict, rule_values: list[str]) -> bool:
    if not rule_values:
        return True
    payload = {
        "add": [
            {"value": v, "tag": f"cryptotimes_{i}"}
            for i, v in enumerate(rule_values)
        ]
    }
    try:
        r = httpx.post(
            f"{TWITTER_API_BASE}/tweets/search/stream/rules",
            headers=headers,
            json=payload,
            timeout=15,
        )
        data = r.json()
        if r.status_code in (200, 201):
            summary = data.get("meta", {}).get("summary", {})
            logger.info(
                "Rules added: %d created, %d not_created",
                summary.get("created", 0),
                summary.get("not_created", 0),
            )
            return True
        logger.error("Add rules failed: HTTP %d — %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Add rules error: %s", e)
    return False


def sync_rules(headers: dict, usernames: set[str]) -> bool:
    """
    Replace all stream rules with ones built from `usernames`.
    Returns True on success.
    """
    existing = _get_current_rules(headers)
    if not _delete_rules(headers, existing):
        return False

    rule_values = _build_rules(usernames)
    if not rule_values:
        logger.warning("No Twitter usernames in DB — stream will receive no tweets")
        return True

    ok = _add_rules(headers, rule_values)
    if ok:
        logger.info(
            "Stream rules synced: %d accounts across %d rule(s)",
            len(usernames), len(rule_values),
        )
    return ok


# ── Tweet processing ──────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r"https?://t\.co/\S+", "", text).strip()
    return re.sub(r"\s+", " ", text).strip()


def _process_tweet(tweet_data: dict, includes: dict):
    """Convert a raw stream tweet payload into a NewsArticle."""
    from news.models import NewsArticle, Source

    tweet = tweet_data.get("data", {})
    tweet_id = tweet.get("id", "")
    raw_text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")

    if not raw_text or len(raw_text) < MIN_TWEET_LENGTH:
        return
    if raw_text.strip().startswith("RT @") or raw_text.strip().startswith("@"):
        return  # skip retweets and replies

    clean_text = _clean_text(raw_text)
    if not clean_text or len(clean_text) < 20:
        return
    if not is_crypto_related(clean_text, clean_text):
        return

    # Resolve username from includes
    username = ""
    for user in includes.get("users", []):
        if user.get("id") == author_id:
            username = user.get("username", "")
            break

    if not username:
        logger.debug("Could not resolve username for author_id %s", author_id)
        return

    # Find the matching Source row
    source = None
    username_lower = username.lower()
    for src in Source.objects.filter(source_type="twitter", is_active=True):
        raw = (src.url or "").strip()
        if raw.upper() == "ALL":
            continue
        if _extract_username(raw).lower() == username_lower:
            source = src
            break

    if not source:
        logger.debug("No active source found for @%s — skipping", username)
        return

    # Extract media images
    media_map = {
        m.get("media_key", ""): (m.get("url") or m.get("preview_image_url", ""))
        for m in includes.get("media", [])
        if m.get("media_key")
    }
    images = [
        media_map[k]
        for k in tweet.get("attachments", {}).get("media_keys", [])
        if k in media_map
    ]

    # Deduplication
    external_id = hashlib.sha256(
        f"{source.id}:tweet:{tweet_id}".encode()
    ).hexdigest()[:64]

    if NewsArticle.objects.filter(external_id=external_id).exists():
        return

    title = clean_text[:120] + ("…" if len(clean_text) > 120 else "")
    if NewsArticle.objects.filter(title=title).exists():
        return

    tweet_url = f"https://x.com/{username}/status/{tweet_id}"
    metrics = tweet.get("public_metrics", {})
    likes = metrics.get("like_count", 0)
    rt_count = metrics.get("retweet_count", 0)
    engagement = (
        f" (Engagement: {likes:,} likes, {rt_count:,} retweets)"
        if likes > 100 or rt_count > 50
        else ""
    )

    article = NewsArticle.objects.create(
        title=title,
        summary=clean_text[:300],
        content=f"<p>{clean_text}{engagement}</p>",
        source=source,
        original_url=tweet_url,
        images=images,
        external_id=external_id,
        status="pending",
    )

    logger.info("Stream → new article: @%s — %s", username, title[:60])
    _executor.submit(_verify_and_image, article)


def _verify_and_image(article):
    try:
        from news.ai.verifier import verify_article
        verify_article(article)
    except Exception as e:
        logger.error("Stream verify error for '%s': %s", article.title[:40], e)
    try:
        from news.scrapers.images import ensure_article_images
        ensure_article_images(article, min_images=2, max_images=3)
    except Exception as e:
        logger.error("Stream image error for '%s': %s", article.title[:40], e)


# ── Stream loop ───────────────────────────────────────────────

def _run_stream(headers: dict, stop_event: threading.Event):
    reconnect_delay = RECONNECT_DELAY_BASE
    last_rules_check = 0.0
    current_usernames: set[str] = set()

    while not stop_event.is_set():
        # Sync rules before connecting (or when sources change)
        now = time.monotonic()
        if now - last_rules_check >= RULES_REFRESH_INTERVAL:
            try:
                new_usernames = _load_usernames_from_db()
                if new_usernames != current_usernames:
                    logger.info(
                        "Twitter sources changed (%d → %d), syncing rules...",
                        len(current_usernames), len(new_usernames),
                    )
                    sync_rules(headers, new_usernames)
                    current_usernames = new_usernames
                last_rules_check = time.monotonic()
            except Exception as e:
                logger.error("Rules sync error: %s", e)

        params = {
            "tweet.fields": "created_at,text,attachments,entities,public_metrics,author_id",
            "expansions": "author_id,attachments.media_keys",
            "user.fields": "username,name",
            "media.fields": "url,preview_image_url,type",
        }

        logger.info("Connecting to Twitter Filtered Stream...")

        try:
            with httpx.stream(
                "GET",
                f"{TWITTER_API_BASE}/tweets/search/stream",
                headers=_stream_headers(headers),
                params=params,
                timeout=httpx.Timeout(connect=30.0, read=30.0, write=None, pool=None),
            ) as response:
                if response.status_code != 200:
                    body = response.read().decode(errors="replace")
                    logger.error(
                        "Stream connection failed: HTTP %d — %s",
                        response.status_code, body[:300],
                    )
                    sleep_time = 60 if response.status_code == 429 else reconnect_delay
                    time.sleep(sleep_time)
                    reconnect_delay = min(reconnect_delay * 2, RECONNECT_DELAY_MAX)
                    continue

                logger.info("Connected to Twitter Filtered Stream")
                reconnect_delay = RECONNECT_DELAY_BASE  # reset on success

                for line in response.iter_lines():
                    if stop_event.is_set():
                        break

                    if not line.strip():
                        # Empty line = heartbeat keepalive (every ~20 s)
                        continue

                    # Periodically check for source list changes
                    now = time.monotonic()
                    if now - last_rules_check >= RULES_REFRESH_INTERVAL:
                        try:
                            new_usernames = _load_usernames_from_db()
                            if new_usernames != current_usernames:
                                logger.info(
                                    "Source list changed while streaming — reconnecting to update rules"
                                )
                                current_usernames = new_usernames
                                last_rules_check = time.monotonic()
                                break  # reconnect loop will sync rules
                            last_rules_check = time.monotonic()
                        except Exception as e:
                            logger.error("Source refresh error: %s", e)

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if "data" not in data:
                        # Could be an error object
                        if "errors" in data:
                            logger.warning("Stream error object: %s", data["errors"])
                        continue

                    try:
                        _process_tweet(data, data.get("includes", {}))
                    except Exception as e:
                        logger.error("Tweet processing error: %s", e)

        except httpx.ReadTimeout:
            logger.warning("Stream read timeout — reconnecting in %ds", reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, RECONNECT_DELAY_MAX)
        except Exception as e:
            if stop_event.is_set():
                break
            logger.error("Stream error: %s — reconnecting in %ds", e, reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, RECONNECT_DELAY_MAX)

    logger.info("Twitter Filtered Stream stopped")


# ── Public API ────────────────────────────────────────────────

def start_stream():
    """
    Start the Twitter Filtered Stream in a daemon background thread.
    Idempotent — safe to call multiple times.
    """
    global _stream_thread, _stop_event

    if _stream_thread and _stream_thread.is_alive():
        logger.debug("Twitter stream already running")
        return

    token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
    if not token:
        logger.warning("TWITTER_BEARER_TOKEN not set — Twitter Filtered Stream disabled")
        return

    headers = _get_headers()

    # Initial rule sync before thread starts
    try:
        usernames = _load_usernames_from_db()
        sync_rules(headers, usernames)
    except Exception as e:
        logger.error("Initial rule sync failed: %s — stream will retry on connect", e)

    _stop_event = threading.Event()
    _stream_thread = threading.Thread(
        target=_run_stream,
        args=(headers, _stop_event),
        daemon=True,
        name="twitter-filtered-stream",
    )
    _stream_thread.start()
    logger.info("Twitter Filtered Stream thread started")


def stop_stream():
    """Signal the stream thread to stop (for testing / graceful shutdown)."""
    if _stop_event:
        _stop_event.set()
