"""
AI Verification module for The Crypto Times.

Supports three providers:
  - mock:      Deterministic scores for development (no API key needed)
  - anthropic: Claude API
  - openai:    GPT-4o API

Set AI_PROVIDER and the relevant API key in .env.
"""

import json
import hashlib
import logging
import random
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("news")


@dataclass
class VerificationResult:
    verdict: str  # REAL | FAKE | UNCERTAIN
    confidence: float  # 0–100
    explanation: str
    raw: dict


# ── Provider: Mock ──────────────────────────────────────────
def _verify_mock(title: str, content: str) -> VerificationResult:
    """Deterministic but varied mock results based on content hash."""
    h = int(hashlib.md5((title + content[:200]).encode()).hexdigest(), 16)
    bucket = h % 100

    if bucket < 60:
        verdict, conf = "REAL", 75 + (bucket % 20)
    elif bucket < 80:
        verdict, conf = "UNCERTAIN", 40 + (bucket % 30)
    else:
        verdict, conf = "FAKE", 60 + (bucket % 25)

    explanations = {
        "REAL": (
            "The article references verifiable on-chain data and cites "
            "reputable sources. Key claims are consistent with publicly "
            "available information from blockchain explorers and official "
            "press releases."
        ),
        "FAKE": (
            "Several claims in this article cannot be corroborated. The "
            "quoted statistics do not match publicly available data, and "
            "the attributed sources have no record of the statements "
            "mentioned."
        ),
        "UNCERTAIN": (
            "The article contains a mix of verifiable and unverifiable "
            "claims. While the general topic is accurate, specific figures "
            "and quotes could not be independently confirmed at this time."
        ),
    }

    return VerificationResult(
        verdict=verdict,
        confidence=min(conf, 99),
        explanation=explanations[verdict],
        raw={"provider": "mock", "hash": h % 10000},
    )


# ── Provider: Anthropic Claude ──────────────────────────────
def _verify_anthropic(title: str, content: str) -> VerificationResult:
    """Call Claude API for verification."""
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
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return _parse_ai_response(
        data["content"][0]["text"],
        raw=data,
        provider="anthropic",
    )


# ── Provider: OpenAI ────────────────────────────────────────
def _verify_openai(title: str, content: str) -> VerificationResult:
    """Call OpenAI API for verification."""
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
            "max_tokens": 1024,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return _parse_ai_response(
        data["choices"][0]["message"]["content"],
        raw=data,
        provider="openai",
    )


# ── Shared helpers ──────────────────────────────────────────
def _build_prompt(title: str, content: str) -> str:
    """Build the verification prompt shared across providers."""
    truncated = content[:3000]
    return f"""You are a crypto news verification AI. Analyze the following article and determine if it is REAL, FAKE, or UNCERTAIN.

TITLE: {title}

CONTENT:
{truncated}

Respond ONLY with valid JSON (no markdown fences):
{{
  "verdict": "REAL" | "FAKE" | "UNCERTAIN",
  "confidence": <number 0-100>,
  "explanation": "<2-3 sentence explanation>"
}}"""


def _parse_ai_response(text: str, raw: dict, provider: str) -> VerificationResult:
    """Parse the JSON response from any AI provider."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON: %s", cleaned[:200])
        return VerificationResult(
            verdict="UNCERTAIN",
            confidence=30,
            explanation="AI response could not be parsed.",
            raw={"error": "parse_failure", "text": cleaned[:500], "provider": provider},
        )

    verdict = parsed.get("verdict", "UNCERTAIN").upper()
    if verdict not in ("REAL", "FAKE", "UNCERTAIN"):
        verdict = "UNCERTAIN"

    return VerificationResult(
        verdict=verdict,
        confidence=max(0, min(100, float(parsed.get("confidence", 50)))),
        explanation=parsed.get("explanation", ""),
        raw={**raw, "provider": provider},
    )


# ── Main entry point ───────────────────────────────────────
PROVIDERS = {
    "mock": _verify_mock,
    "anthropic": _verify_anthropic,
    "openai": _verify_openai,
}


def verify_article(article) -> VerificationResult:
    """
    Run AI verification on a NewsArticle instance.
    Updates the article fields and creates a VerificationLog entry.
    """
    from news.models import VerificationLog

    provider_name = settings.AI_PROVIDER
    provider_fn = PROVIDERS.get(provider_name, _verify_mock)

    logger.info("Verifying article '%s' with provider=%s", article.title[:50], provider_name)

    try:
        result = provider_fn(article.title, article.content)
    except Exception as e:
        logger.error("AI verification failed: %s", e)
        result = VerificationResult(
            verdict="UNCERTAIN",
            confidence=0,
            explanation=f"Verification error: {e}",
            raw={"error": str(e)},
        )

    # Update article
    article.ai_verdict = result.verdict
    article.confidence_score = result.confidence
    article.save(update_fields=["ai_verdict", "confidence_score", "updated_at"])

    # Create log entry
    VerificationLog.objects.create(
        article=article,
        verdict=result.verdict,
        confidence_score=result.confidence,
        explanation=result.explanation,
        provider=provider_name,
        raw_response=result.raw,
    )

    logger.info(
        "Verdict: %s (%.0f%%) for '%s'",
        result.verdict,
        result.confidence,
        article.title[:50],
    )

    return result
