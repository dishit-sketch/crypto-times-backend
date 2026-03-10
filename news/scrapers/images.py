"""
Auto-fetch crypto-related images for articles that lack them.
Uses Unsplash API if key is set, otherwise provides curated fallback URLs.
"""

import logging
import random
import httpx
from django.conf import settings

logger = logging.getLogger("news")

# Curated fallback images — royalty-free Unsplash crypto/finance photos
FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=800&q=80",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
    "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&q=80",
    "https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=800&q=80",
    "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=800&q=80",
    "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=800&q=80",
    "https://images.unsplash.com/photo-1621504450181-5d356f61d307?w=800&q=80",
    "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=800&q=80",
    "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=800&q=80",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80",
    "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?w=800&q=80",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&q=80",
    "https://images.unsplash.com/photo-1646463535685-f0cf42cb3127?w=800&q=80",
    "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=800&q=80",
]


def fetch_images_for_keywords(keywords: list[str], count: int = 3) -> list[str]:
    """
    Fetch images from Unsplash for given keywords.
    Falls back to curated list if no API key or request fails.
    """
    api_key = settings.UNSPLASH_ACCESS_KEY

    if api_key:
        try:
            query = " ".join(keywords[:3]) + " cryptocurrency"
            resp = httpx.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": count, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            urls = [
                photo["urls"]["regular"]
                for photo in data.get("results", [])[:count]
            ]
            if urls:
                return urls
        except Exception as e:
            logger.warning("Unsplash API failed: %s — using fallbacks", e)

    # Fallback: pick random curated images
    return random.sample(FALLBACK_IMAGES, min(count, len(FALLBACK_IMAGES)))


def ensure_article_images(article, min_images: int = 2, max_images: int = 3):
    """
    Ensure an article has at least `min_images`.
    If not, auto-fetch using title keywords.
    """
    current = article.images if isinstance(article.images, list) else []

    if len(current) >= min_images:
        return

    needed = max_images - len(current)
    keywords = article.title.split()[:5]
    new_images = fetch_images_for_keywords(keywords, count=needed)
    article.images = current + new_images
    article.save(update_fields=["images", "updated_at"])
    logger.info("Added %d images to '%s'", len(new_images), article.title[:50])
