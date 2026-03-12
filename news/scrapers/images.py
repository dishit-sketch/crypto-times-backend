"""
Auto-fetch crypto-related images for articles.
Uses category-matched fallback images when source has none.
"""

import logging
import random
import httpx
from django.conf import settings

logger = logging.getLogger("news")

# Category-specific curated images (royalty-free from Unsplash)
CATEGORY_IMAGES = {
    "Markets": [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=800&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=800&q=80",
        "https://images.unsplash.com/photo-1468254095679-bbcba94a7066?w=800&q=80",
    ],
    "DeFi": [
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&q=80",
        "https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=800&q=80",
        "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=800&q=80",
        "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?w=800&q=80",
    ],
    "Regulation": [
        "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&q=80",
        "https://images.unsplash.com/photo-1436450412740-6b988f486c6b?w=800&q=80",
        "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=800&q=80",
        "https://images.unsplash.com/photo-1575505586569-646b2ca898fc?w=800&q=80",
    ],
    "Technology": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80",
    ],
    "Security": [
        "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=800&q=80",
        "https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=800&q=80",
        "https://images.unsplash.com/photo-1510511459019-5dda7724fd87?w=800&q=80",
        "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=800&q=80",
    ],
    "NFT": [
        "https://images.unsplash.com/photo-1646463535685-f0cf42cb3127?w=800&q=80",
        "https://images.unsplash.com/photo-1645731504599-3e2e1ef44c2d?w=800&q=80",
        "https://images.unsplash.com/photo-1637611331620-51149e7a01f5?w=800&q=80",
        "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=800&q=80",
    ],
    "CBDC": [
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80",
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=800&q=80",
        "https://images.unsplash.com/photo-1604594849809-dfedbc827105?w=800&q=80",
    ],
    "General": [
        "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=800&q=80",
        "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=800&q=80",
        "https://images.unsplash.com/photo-1621504450181-5d356f61d307?w=800&q=80",
        "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=800&q=80",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&q=80",
    ],
}

# Keyword to category mapping for image selection
KEYWORD_IMAGE_MAP = {
    "bitcoin": "Markets",
    "btc": "Markets",
    "price": "Markets",
    "etf": "Markets",
    "market": "Markets",
    "trading": "Markets",
    "ethereum": "DeFi",
    "defi": "DeFi",
    "uniswap": "DeFi",
    "aave": "DeFi",
    "sec": "Regulation",
    "regulation": "Regulation",
    "law": "Regulation",
    "ban": "Regulation",
    "hack": "Security",
    "scam": "Security",
    "phishing": "Security",
    "exploit": "Security",
    "nft": "NFT",
    "layer 2": "Technology",
    "upgrade": "Technology",
    "blockchain": "Technology",
    "cbdc": "CBDC",
    "digital currency": "CBDC",
}


def _is_valid_image_url(url: str) -> bool:
    """Check if an image URL is likely to work."""
    if not url or not url.startswith("http"):
        return False
    # Skip tiny tracking pixels and icons
    skip_patterns = [
        "pixel", "tracking", "1x1", "spacer", "blank",
        "favicon", "icon", "logo", "badge", "button",
        "avatar", "gravatar", "widget",
    ]
    url_lower = url.lower()
    return not any(p in url_lower for p in skip_patterns)


def _get_category_for_article(title: str, category: str) -> str:
    """Determine the best image category based on title and category."""
    if category and category in CATEGORY_IMAGES:
        return category

    title_lower = title.lower()
    for keyword, cat in KEYWORD_IMAGE_MAP.items():
        if keyword in title_lower:
            return cat

    return "General"


def get_images_for_article(title: str, category: str = "", count: int = 3) -> list[str]:
    """Get category-matched images for an article."""
    img_category = _get_category_for_article(title, category)
    pool = CATEGORY_IMAGES.get(img_category, CATEGORY_IMAGES["General"])
    return random.sample(pool, min(count, len(pool)))


def ensure_article_images(article, min_images: int = 2, max_images: int = 3):
    """
    Ensure an article has at least min_images valid images.
    Replaces broken/invalid images and adds category-matched ones.
    """
    current = article.images if isinstance(article.images, list) else []

    # Filter out invalid image URLs
    valid_images = [url for url in current if _is_valid_image_url(url)]

    if len(valid_images) >= min_images:
        # Update if we removed any invalid ones
        if len(valid_images) != len(current):
            article.images = valid_images[:max_images]
            article.save(update_fields=["images", "updated_at"])
        return

    # Need more images — get category-matched ones
    needed = max_images - len(valid_images)
    category = getattr(article, "category", "") or ""
    new_images = get_images_for_article(article.title, category, count=needed)

    # Avoid duplicates
    existing_set = set(valid_images)
    for img in new_images:
        if img not in existing_set:
            valid_images.append(img)
            existing_set.add(img)

    article.images = valid_images[:max_images]
    article.save(update_fields=["images", "updated_at"])
    logger.info("Set %d images for '%s' (category: %s)", len(article.images), article.title[:50], category)
