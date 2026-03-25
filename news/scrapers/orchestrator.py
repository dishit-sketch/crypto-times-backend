"""
Central orchestrator for news scraping.
Dispatches to the correct scraper based on source type,
then runs AI verification and ensures images.
Includes on-chain whale monitoring.
"""

import logging
import time
from news.models import Source, SourceType
from news.scrapers.rss_scraper import scrape_rss_source
from news.scrapers.website_scraper import scrape_website_source
from news.scrapers.twitter_scraper import scrape_twitter_source
from news.scrapers.whale_scraper import scrape_whale_source
from news.scrapers.images import ensure_article_images
from news.ai.verifier import verify_article

logger = logging.getLogger("news")

# ── Rate limiting for Groq free tier ────────────────────────
MAX_VERIFICATIONS_PER_CYCLE = 10
VERIFICATION_DELAY_SECONDS = 7


SCRAPER_MAP = {
    SourceType.RSS: scrape_rss_source,
    SourceType.WEBSITE: scrape_website_source,
    SourceType.TWITTER: scrape_twitter_source,
}


def fetch_all_sources():
    """
    Fetch news from all active sources, verify with AI, and ensure images.
    Called by the scheduler every N minutes.
    Also runs whale monitoring for on-chain alerts.
    """
    active_sources = Source.objects.filter(is_active=True)
    total_created = 0
    verifications_this_cycle = 0

    logger.info("Starting fetch cycle for %d active sources", active_sources.count())

    for source in active_sources:
        # ── Handle whale monitor source type ────────────────
        if source.url == "WHALE_MONITOR":
            try:
                articles = scrape_whale_source(source)
                logger.info("Whale monitor: %d new alerts", len(articles))

                for article in articles:
                    # Whale alerts already have verdict and confidence set
                    # Only run AI verification if not already set
                    if article.confidence_score == 0:
                        if verifications_this_cycle < MAX_VERIFICATIONS_PER_CYCLE:
                            try:
                                verify_article(article)
                                verifications_this_cycle += 1
                                time.sleep(VERIFICATION_DELAY_SECONDS)
                            except Exception as e:
                                logger.error("Verification failed for '%s': %s", article.title[:40], e)

                    # Ensure images
                    try:
                        ensure_article_images(article, min_images=2, max_images=3)
                    except Exception as e:
                        logger.error("Image fetch failed for '%s': %s", article.title[:40], e)

                total_created += len(articles)
            except Exception as e:
                logger.error("Whale monitor error: %s", e)
            continue

        # ── Skip Twitter sources — handled by Filtered Stream ──
        if source.type == SourceType.TWITTER:
            continue

        # ── Handle regular sources ──────────────────────────
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

                # Run AI verification (with rate limiting)
                if verifications_this_cycle < MAX_VERIFICATIONS_PER_CYCLE:
                    try:
                        verify_article(article)
                        verifications_this_cycle += 1
                        time.sleep(VERIFICATION_DELAY_SECONDS)
                    except Exception as e:
                        logger.error("Verification failed for '%s': %s", article.title[:40], e)
                else:
                    logger.info(
                        "Skipping AI verification for '%s' — reached max %d per cycle",
                        article.title[:40], MAX_VERIFICATIONS_PER_CYCLE,
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
        total_created, verifications_this_cycle,
    )
    return total_created


def fetch_single_source(source_id: str) -> int:
    """Fetch news from a single source by ID."""
    try:
        source = Source.objects.get(id=source_id, is_active=True)
    except Source.DoesNotExist:
        logger.error("Source %s not found or inactive", source_id)
        return 0

    if source.url == "WHALE_MONITOR":
        articles = scrape_whale_source(source)
    else:
        scraper = SCRAPER_MAP.get(source.type)
        if not scraper:
            return 0
        articles = scraper(source)

    for article in articles:
        try:
            verify_article(article)
        except Exception:
            pass
        try:
            ensure_article_images(article)
        except Exception:
            pass

    return len(articles)
