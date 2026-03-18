"""
Central orchestrator for news scraping.
Dispatches to the correct scraper based on source type,
then runs AI verification and ensures images.
"""

import logging
import time
from news.models import Source, SourceType
from news.scrapers.rss_scraper import scrape_rss_source
from news.scrapers.website_scraper import scrape_website_source
from news.scrapers.twitter_scraper import scrape_twitter_source
from news.scrapers.images import ensure_article_images
from news.ai.verifier import verify_article

logger = logging.getLogger("news")

SCRAPER_MAP = {
    SourceType.RSS: scrape_rss_source,
    SourceType.WEBSITE: scrape_website_source,
    SourceType.TWITTER: scrape_twitter_source,
}

# Max articles to verify per fetch cycle — prevents hitting Groq rate limit
MAX_VERIFICATIONS_PER_CYCLE = 10

# Delay between each AI verification in seconds
VERIFICATION_DELAY_SECONDS = 4


def fetch_all_sources():
    """
    Fetch news from all active sources, verify with AI, and ensure images.
    Called by the scheduler every N minutes.
    """
    active_sources = Source.objects.filter(is_active=True)
    total_created = 0
    verifications_this_cycle = 0

    logger.info("Starting fetch cycle for %d active sources", active_sources.count())

    for source in active_sources:
        scraper = SCRAPER_MAP.get(source.type)
        if not scraper:
            logger.warning("No scraper for source type: %s", source.type)
            continue

        try:
            articles = scraper(source)
            logger.info("Fetched %d new articles from '%s'", len(articles), source.name)

            for article in articles:

                # Double-check crypto relevance
                from news.scrapers.crypto_filter import is_crypto_related
                if not is_crypto_related(article.title, article.summary):
                    article.delete()
                    continue

                # Run AI verification — with rate limit protection
                if verifications_this_cycle < MAX_VERIFICATIONS_PER_CYCLE:
                    try:
                        # Add delay between verifications to avoid 429
                        if verifications_this_cycle > 0:
                            time.sleep(VERIFICATION_DELAY_SECONDS)

                        verify_article(article)
                        verifications_this_cycle += 1
                    except Exception as e:
                        logger.error("Verification failed for '%s': %s", article.title[:40], e)
                else:
                    logger.info(
                        "Rate limit protection: skipping verification for '%s' (max %d/cycle reached)",
                        article.title[:40], MAX_VERIFICATIONS_PER_CYCLE
                    )

                # Ensure at least 2 images
                try:
                    ensure_article_images(article, min_images=2, max_images=3)
                except Exception as e:
                    logger.error("Image fetch failed for '%s': %s", article.title[:40], e)

            total_created += len(articles)

        except Exception as e:
            logger.error("Scraper error for '%s': %s", source.name, e)

    logger.info(
        "Fetch cycle complete: %d new articles total, %d verified with AI",
        total_created, verifications_this_cycle
    )
    return total_created


def fetch_single_source(source_id: str) -> int:
    """Fetch news from a single source by ID."""
    try:
        source = Source.objects.get(id=source_id, is_active=True)
    except Source.DoesNotExist:
        logger.error("Source %s not found or inactive", source_id)
        return 0

    scraper = SCRAPER_MAP.get(source.type)
    if not scraper:
        return 0

    articles = scraper(source)
    for article in articles:
        try:
            time.sleep(VERIFICATION_DELAY_SECONDS)
            verify_article(article)
        except Exception:
            pass
        try:
            ensure_article_images(article)
        except Exception:
            pass

    return len(articles)
