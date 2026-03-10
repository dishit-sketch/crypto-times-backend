"""
Website scraper for The Crypto Times.
Scrapes news articles from crypto websites by finding links and extracting content.
"""

import logging
import hashlib
import re
import httpx
from bs4 import BeautifulSoup
from django.utils import timezone
from django.utils.html import strip_tags

from news.models import NewsArticle, Source

logger = logging.getLogger("news")

# Common patterns for news article links
ARTICLE_PATTERNS = [
    r"/\d{4}/\d{2}/",       # /2026/03/
    r"/news/",
    r"/article/",
    r"/post/",
    r"/blog/",
]


def scrape_website_source(source: Source) -> list[NewsArticle]:
    """Scrape a crypto website for new articles."""
    logger.info("Scraping website: %s (%s)", source.name, source.url)
    created = []

    try:
        resp = httpx.get(
            source.url,
            headers={
                "User-Agent": "TheCryptoTimes/1.0 NewsBot",
                "Accept": "text/html",
            },
            follow_redirects=True,
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch %s: %s", source.url, e)
        return created

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find article links
    article_links = _find_article_links(soup, source.url)
    logger.info("Found %d potential article links on %s", len(article_links), source.name)

    for link_url, link_title in article_links[:10]:  # Process top 10
        external_id = hashlib.sha256(f"{source.id}:{link_url}".encode()).hexdigest()[:64]

        if NewsArticle.objects.filter(external_id=external_id).exists():
            continue

        # Fetch article page
        try:
            article_data = _extract_article(link_url)
        except Exception as e:
            logger.warning("Failed to extract %s: %s", link_url, e)
            continue

        if not article_data:
            continue

        title = article_data.get("title") or link_title
        if not title:
            continue

        article = NewsArticle.objects.create(
            title=title,
            summary=article_data.get("summary", title)[:300],
            content=article_data.get("content", f"<p>{article_data.get('summary', '')}</p>"),
            source=source,
            original_url=link_url,
            author=article_data.get("author", ""),
            images=article_data.get("images", []),
            external_id=external_id,
        )
        created.append(article)
        logger.info("Created article: %s", title[:60])

    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return created


def _find_article_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
    """Find links that look like news articles."""
    from urllib.parse import urljoin, urlparse

    base_domain = urlparse(base_url).netloc
    results = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Same domain only
        if parsed.netloc != base_domain:
            continue

        # Skip non-article links
        path = parsed.path.lower()
        if any(skip in path for skip in ["/tag/", "/category/", "/author/", "/page/", "#"]):
            continue

        # Match article patterns
        is_article = any(re.search(pat, path) for pat in ARTICLE_PATTERNS)
        # Or has a long-ish path segment (slug)
        segments = [s for s in path.split("/") if s]
        has_slug = any(len(s) > 15 for s in segments)

        if not (is_article or has_slug):
            continue

        if full_url in seen:
            continue
        seen.add(full_url)

        title = a_tag.get_text(strip=True)[:200]
        if len(title) > 10:  # Skip short/empty link texts
            results.append((full_url, title))

    return results


def _extract_article(url: str) -> dict | None:
    """Fetch and extract content from a single article page."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "TheCryptoTimes/1.0 NewsBot"},
            follow_redirects=True,
            timeout=15,
        )
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title = ""
    for sel in ["h1", "meta[property='og:title']", "title"]:
        el = soup.select_one(sel)
        if el:
            title = el.get("content") if el.name == "meta" else el.get_text(strip=True)
            if title:
                break

    # Content — try common article containers
    content = ""
    for sel in ["article", "[class*='article-body']", "[class*='post-content']", "[class*='entry-content']", "main"]:
        el = soup.select_one(sel)
        if el:
            # Remove scripts, nav, footer
            for tag in el.find_all(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()
            content = str(el)
            break

    summary = ""
    meta_desc = soup.select_one("meta[name='description']") or soup.select_one("meta[property='og:description']")
    if meta_desc:
        summary = meta_desc.get("content", "")

    if not summary and content:
        summary = strip_tags(content)[:300].strip()

    # Images
    images = []
    og_img = soup.select_one("meta[property='og:image']")
    if og_img and og_img.get("content"):
        images.append(og_img["content"])

    if content:
        content_soup = BeautifulSoup(content, "html.parser")
        for img in content_soup.find_all("img", src=True)[:5]:
            src = img["src"]
            if src.startswith("http") and src not in images:
                images.append(src)

    # Author
    author = ""
    author_meta = soup.select_one("meta[name='author']")
    if author_meta:
        author = author_meta.get("content", "")

    if not title:
        return None

    return {
        "title": title[:500],
        "summary": summary[:300],
        "content": content or f"<p>{summary}</p>",
        "author": author[:255],
        "images": images[:5],
    }
