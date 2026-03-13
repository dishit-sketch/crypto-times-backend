"""
AI Verification + Content Generation for CryptoTimes.io

Supports providers:
  - mock:     Development mode (no API key needed)
  - alibaba:  Alibaba Cloud Qwen (primary) — verification + description + images
  - anthropic: Claude API (fallback)
  - openai:   GPT-4o (fallback)

Set AI_PROVIDER and ALIBABA_API_KEY in .env
"""

import json
import hashlib
import logging
import random
import re
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("news")


@dataclass
class VerificationResult:
    verdict: str       # REAL | FAKE | UNCERTAIN
    confidence: float  # 0–100
    explanation: str
    description: str   # AI-generated article description
    raw: dict


# ══════════════════════════════════════════════════════════
# ALIBABA QWEN PROVIDER
# ══════════════════════════════════════════════════════════

def _verify_alibaba(title: str, content: str) -> VerificationResult:
    """Verify article + generate description using Alibaba Qwen API."""
    import httpx

    api_key = settings.ALIBABA_API_KEY

    prompt = f"""You are a crypto news verification AI for CryptoTimes.io. 
Analyze this article and:
1. Determine if it is REAL, FAKE, or UNCERTAIN
2. Give a confidence score 0-100
3. Write an explanation (2-3 sentences)
4. Write a professional news article description (10-15 sentences) that expands on the original content with factual crypto market context. Write it as if you are a senior crypto journalist. Include relevant market data, historical context, and expert analysis perspective.

TITLE: {title}

CONTENT:
{content[:3000]}

Respond ONLY with valid JSON (no markdown fences):
{{
  "verdict": "REAL" | "FAKE" | "UNCERTAIN",
  "confidence": <number 0-100>,
  "explanation": "<2-3 sentence verification explanation>",
  "description": "<10-15 sentence professional article description>"
}}"""

    response = httpx.post(
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    text = data["choices"][0]["message"]["content"]
    return _parse_ai_response_with_desc(text, raw=data, provider="alibaba")


def _generate_images_alibaba(title: str, category: str = "") -> list[str]:
    """Generate 2 images using Alibaba Wanx image generation API."""
    import httpx
    import time

    api_key = settings.ALIBABA_API_KEY
    if not api_key:
        return []

    prompt = (
        f"Professional cryptocurrency news illustration for article titled: '{title[:100]}'. "
        f"Category: {category or 'crypto'}. "
        "Style: modern, clean, professional financial news imagery. "
        "Include relevant crypto symbols, charts, or blockchain visuals. "
        "High quality, photorealistic, editorial style."
    )

    try:
        # Submit image generation task
        response = httpx.post(
            "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json={
                "model": "wanx-v1",
                "input": {"prompt": prompt},
                "parameters": {
                    "n": 2,
                    "size": "1024*576",
                    "style": "<photography>",
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        task_data = response.json()

        task_id = task_data.get("output", {}).get("task_id")
        if not task_id:
            logger.warning("Alibaba image: no task_id returned")
            return []

        # Poll for results
        for _ in range(30):  # Max 60 seconds
            time.sleep(2)
            status_resp = httpx.get(
                f"https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            status_data = status_resp.json()
            task_status = status_data.get("output", {}).get("task_status")

            if task_status == "SUCCEEDED":
                results = status_data.get("output", {}).get("results", [])
                urls = [r.get("url", "") for r in results if r.get("url")]
                logger.info("Alibaba generated %d images for '%s'", len(urls), title[:40])
                return urls[:2]
            elif task_status == "FAILED":
                logger.warning("Alibaba image generation failed for '%s'", title[:40])
                return []

        logger.warning("Alibaba image generation timed out for '%s'", title[:40])
        return []

    except Exception as e:
        logger.error("Alibaba image generation error: %s", e)
        return []


# ══════════════════════════════════════════════════════════
# OTHER PROVIDERS
# ══════════════════════════════════════════════════════════

def _verify_mock(title: str, content: str) -> VerificationResult:
    """Deterministic mock results for development."""
    h = int(hashlib.md5((title + content[:200]).encode()).hexdigest(), 16)
    bucket = h % 100

    if bucket < 60:
        verdict, conf = "REAL", 75 + (bucket % 20)
    elif bucket < 80:
        verdict, conf = "UNCERTAIN", 40 + (bucket % 30)
    else:
        verdict, conf = "FAKE", 60 + (bucket % 25)

    explanations = {
        "REAL": "The article references verifiable on-chain data and cites reputable sources. Key claims are consistent with publicly available information.",
        "FAKE": "Several claims cannot be corroborated. Quoted statistics do not match publicly available data.",
        "UNCERTAIN": "The article contains a mix of verifiable and unverifiable claims. Specific figures could not be independently confirmed.",
    }

    description = (
        f"In a significant development for the cryptocurrency market, {title}. "
        "This latest update reflects the ongoing evolution of the digital asset ecosystem. "
        "Market analysts have been closely monitoring these developments, noting their potential impact on both institutional and retail investors. "
        "The broader cryptocurrency market has shown increased activity in recent weeks, with trading volumes reaching notable levels across major exchanges. "
        "Industry experts suggest that this development could have far-reaching implications for the future of blockchain technology and decentralized finance. "
        "On-chain data indicates growing adoption metrics, with active addresses and transaction volumes trending upward. "
        "Regulatory bodies worldwide continue to refine their frameworks for digital assets, creating a more structured environment for market participants. "
        "The DeFi sector has also seen renewed interest, with total value locked across protocols maintaining strong levels. "
        "As the crypto industry matures, developments like these highlight the sector's resilience and growing mainstream acceptance. "
        "Investors are advised to conduct thorough research and consider multiple sources before making investment decisions."
    )

    return VerificationResult(
        verdict=verdict,
        confidence=min(conf, 99),
        explanation=explanations[verdict],
        description=description,
        raw={"provider": "mock", "hash": h % 10000},
    )


def _verify_anthropic(title: str, content: str) -> VerificationResult:
    """Call Claude API."""
    import httpx

    prompt = _build_prompt(title, content)
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return _parse_ai_response_with_desc(data["content"][0]["text"], raw=data, provider="anthropic")


def _verify_openai(title: str, content: str) -> VerificationResult:
    """Call OpenAI API."""
    import httpx

    prompt = _build_prompt(title, content)
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return _parse_ai_response_with_desc(data["choices"][0]["message"]["content"], raw=data, provider="openai")


# ══════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════

def _build_prompt(title: str, content: str) -> str:
    """Shared prompt for all providers."""
    return f"""You are a crypto news verification AI for CryptoTimes.io.
Analyze this article and:
1. Determine if it is REAL, FAKE, or UNCERTAIN
2. Give a confidence score 0-100
3. Write a verification explanation (2-3 sentences)
4. Write a professional news description (10-15 sentences) expanding on the content with crypto market context, written as a senior crypto journalist.

TITLE: {title}

CONTENT:
{content[:3000]}

Respond ONLY with valid JSON (no markdown fences):
{{
  "verdict": "REAL" | "FAKE" | "UNCERTAIN",
  "confidence": <number 0-100>,
  "explanation": "<2-3 sentence verification explanation>",
  "description": "<10-15 sentence professional article description>"
}}"""


def _parse_ai_response_with_desc(text: str, raw: dict, provider: str) -> VerificationResult:
    """Parse JSON response that includes description field."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON: %s", cleaned[:200])
        return VerificationResult(
            verdict="UNCERTAIN", confidence=30,
            explanation="AI response could not be parsed.",
            description="",
            raw={"error": "parse_failure", "text": cleaned[:500], "provider": provider},
        )

    verdict = parsed.get("verdict", "UNCERTAIN").upper()
    if verdict not in ("REAL", "FAKE", "UNCERTAIN"):
        verdict = "UNCERTAIN"

    return VerificationResult(
        verdict=verdict,
        confidence=max(0, min(100, float(parsed.get("confidence", 50)))),
        explanation=parsed.get("explanation", ""),
        description=parsed.get("description", ""),
        raw={**raw, "provider": provider},
    )


# ══════════════════════════════════════════════════════════
# MAIN ENTRY POINTS
# ══════════════════════════════════════════════════════════

PROVIDERS = {
    "mock": _verify_mock,
    "alibaba": _verify_alibaba,
    "anthropic": _verify_anthropic,
    "openai": _verify_openai,
}


def verify_article(article) -> VerificationResult:
    """
    Run AI verification on a NewsArticle.
    Updates verdict, confidence, description, and creates a VerificationLog.
    """
    from news.models import VerificationLog

    provider_name = settings.AI_PROVIDER
    provider_fn = PROVIDERS.get(provider_name, _verify_mock)

    logger.info("Verifying '%s' with provider=%s", article.title[:50], provider_name)

    try:
        result = provider_fn(article.title, article.content)
    except Exception as e:
        logger.error("AI verification failed: %s", e)
        result = VerificationResult(
            verdict="UNCERTAIN", confidence=0,
            explanation=f"Verification error: {e}",
            description="",
            raw={"error": str(e)},
        )

    # Update article fields
    article.ai_verdict = result.verdict
    article.confidence_score = result.confidence
    update_fields = ["ai_verdict", "confidence_score", "updated_at"]

    # Update content with AI description if generated
    if result.description:
        article.content = f"<p>{result.description}</p>"
        article.summary = result.description[:300]
        update_fields.extend(["content", "summary"])

    article.save(update_fields=update_fields)

    # Create verification log
    VerificationLog.objects.create(
        article=article,
        verdict=result.verdict,
        confidence_score=result.confidence,
        explanation=result.explanation,
        provider=provider_name,
        raw_response=result.raw,
    )

    logger.info("Verdict: %s (%.0f%%) for '%s'", result.verdict, result.confidence, article.title[:50])
    return result


def generate_article_content(article):
    """
    Generate AI description + images for an existing article.
    Called from admin "Regenerate content" action.
    """
    provider_name = settings.AI_PROVIDER
    provider_fn = PROVIDERS.get(provider_name, _verify_mock)

    logger.info("Regenerating content for '%s'", article.title[:50])

    # Generate description
    try:
        result = provider_fn(article.title, article.content)
        if result.description:
            article.content = f"<p>{result.description}</p>"
            article.summary = result.description[:300]
    except Exception as e:
        logger.error("Description generation failed: %s", e)

    # Generate images with Alibaba
    if provider_name == "alibaba" and settings.ALIBABA_API_KEY:
        try:
            new_images = _generate_images_alibaba(article.title, article.category)
            if new_images:
                article.images = new_images
        except Exception as e:
            logger.error("Image generation failed: %s", e)

    article.save()
    logger.info("Regenerated content for '%s'", article.title[:50])
