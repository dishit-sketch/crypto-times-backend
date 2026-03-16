"""
AI Verification + Content Generation for CryptoTimes.io

Supports providers:
  - mock:     Development mode (no API key needed)
  - alibaba:  Alibaba Cloud Qwen (primary)
  - anthropic: Claude API (fallback)
  - openai:   GPT-4o (fallback)

Set AI_PROVIDER and ALIBABA_API_KEY in .env
"""

import json
import hashlib
import logging
import random
import re
from dataclasses import dataclass, field

from django.conf import settings

logger = logging.getLogger("news")


@dataclass
class VerificationResult:
    verdict: str        # REAL | FAKE | UNCERTAIN
    confidence: float   # 0–100
    explanation: str
    description: str    # AI-generated article description
    key_points: list    # 3 key bullet points
    raw: dict


# ══════════════════════════════════════════════════════════
# SHARED PROMPT
# ══════════════════════════════════════════════════════════

def _build_prompt(title: str, content: str) -> str:
    return f"""You are a crypto news verification AI for CryptoTimes.io.
Analyze this article and:
1. Determine if it is REAL, FAKE, or UNCERTAIN
2. Give a confidence score 0-100
3. Write a verification explanation (2-3 sentences)
4. Write a professional news description (10-15 sentences) expanding on the content with crypto market context, written as a senior crypto journalist.
5. Extract exactly 3 key points that summarize the most important takeaways from this article. Each key point should be 1-2 sentences.

TITLE: {title}

CONTENT:
{content[:3000]}

Respond ONLY with valid JSON (no markdown fences):
{{
  "verdict": "REAL" | "FAKE" | "UNCERTAIN",
  "confidence": <number 0-100>,
  "explanation": "<2-3 sentence verification explanation>",
  "description": "<10-15 sentence professional article description>",
  "key_points": ["<key point 1>", "<key point 2>", "<key point 3>"]
}}"""


# ══════════════════════════════════════════════════════════
# ALIBABA QWEN PROVIDER
# ══════════════════════════════════════════════════════════

def _verify_alibaba(title: str, content: str) -> VerificationResult:
    import httpx

    api_key = settings.ALIBABA_API_KEY
    prompt = _build_prompt(title, content)

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
    return _parse_ai_response(text, raw=data, provider="alibaba")


def _generate_images_alibaba(title: str, category: str = "") -> list[str]:
    import httpx
    import time

    api_key = settings.ALIBABA_API_KEY
    if not api_key:
        return []

    prompt = (
        f"Professional cryptocurrency news illustration for: '{title[:100]}'. "
        f"Category: {category or 'crypto'}. "
        "Modern, clean, professional financial news imagery. "
        "Crypto symbols, charts, blockchain visuals. Editorial style."
    )

    try:
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
                "parameters": {"n": 2, "size": "1024*576", "style": "<photography>"},
            },
            timeout=30,
        )
        response.raise_for_status()
        task_data = response.json()

        task_id = task_data.get("output", {}).get("task_id")
        if not task_id:
            return []

        for _ in range(30):
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
                return [r.get("url", "") for r in results if r.get("url")][:2]
            elif task_status == "FAILED":
                return []

        return []
    except Exception as e:
        logger.error("Alibaba image error: %s", e)
        return []


# ══════════════════════════════════════════════════════════
# OTHER PROVIDERS
# ══════════════════════════════════════════════════════════

def _verify_mock(title: str, content: str) -> VerificationResult:
    h = int(hashlib.md5((title + content[:200]).encode()).hexdigest(), 16)
    bucket = h % 100

    if bucket < 60:
        verdict, conf = "REAL", 75 + (bucket % 20)
    elif bucket < 80:
        verdict, conf = "UNCERTAIN", 40 + (bucket % 30)
    else:
        verdict, conf = "FAKE", 60 + (bucket % 25)

    explanations = {
        "REAL": "The article references verifiable on-chain data and cites reputable sources.",
        "FAKE": "Several claims cannot be corroborated. Quoted statistics do not match publicly available data.",
        "UNCERTAIN": "The article contains a mix of verifiable and unverifiable claims.",
    }

    description = (
        f"In a significant development for the cryptocurrency market, {title}. "
        "This latest update reflects the ongoing evolution of the digital asset ecosystem. "
        "Market analysts have been closely monitoring these developments. "
        "The broader cryptocurrency market has shown increased activity in recent weeks. "
        "Industry experts suggest far-reaching implications for blockchain technology. "
        "On-chain data indicates growing adoption metrics. "
        "Regulatory bodies worldwide continue to refine their digital asset frameworks. "
        "The DeFi sector has also seen renewed interest with strong TVL levels. "
        "As the crypto industry matures, developments like these highlight growing mainstream acceptance. "
        "Investors are advised to conduct thorough research before making decisions."
    )

    key_points = [
        f"{title.split(' ')[0]} development signals a major shift in the cryptocurrency landscape, with potential implications for both retail and institutional investors.",
        "Market analysts are closely watching on-chain metrics and trading volumes for confirmation of the trend, as regulatory clarity continues to evolve globally.",
        "Industry experts recommend monitoring related developments across DeFi protocols and major exchanges for a complete picture of the market impact.",
    ]

    return VerificationResult(
        verdict=verdict,
        confidence=min(conf, 99),
        explanation=explanations[verdict],
        description=description,
        key_points=key_points,
        raw={"provider": "mock", "hash": h % 10000},
    )


def _verify_anthropic(title: str, content: str) -> VerificationResult:
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
    return _parse_ai_response(data["content"][0]["text"], raw=data, provider="anthropic")


def _verify_openai(title: str, content: str) -> VerificationResult:
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
    return _parse_ai_response(data["choices"][0]["message"]["content"], raw=data, provider="openai")


# ══════════════════════════════════════════════════════════
# RESPONSE PARSER
# ══════════════════════════════════════════════════════════

def _parse_ai_response(text: str, raw: dict, provider: str) -> VerificationResult:
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
            description="", key_points=[],
            raw={"error": "parse_failure", "text": cleaned[:500], "provider": provider},
        )

    verdict = parsed.get("verdict", "UNCERTAIN").upper()
    if verdict not in ("REAL", "FAKE", "UNCERTAIN"):
        verdict = "UNCERTAIN"

    key_points = parsed.get("key_points", [])
    if not isinstance(key_points, list):
        key_points = []
    key_points = [str(kp) for kp in key_points[:3]]

    return VerificationResult(
        verdict=verdict,
        confidence=max(0, min(100, float(parsed.get("confidence", 50)))),
        explanation=parsed.get("explanation", ""),
        description=parsed.get("description", ""),
        key_points=key_points,
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
            description="", key_points=[],
            raw={"error": str(e)},
        )

    # Update article fields
    article.ai_verdict = result.verdict
    article.confidence_score = result.confidence
    update_fields = ["ai_verdict", "confidence_score", "updated_at"]

    if result.description:
        article.content = f"<p>{result.description}</p>"
        article.summary = result.description[:300]
        update_fields.extend(["content", "summary"])

    if result.key_points:
        article.key_points = result.key_points
        update_fields.append("key_points")

    article.save(update_fields=update_fields)

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
    provider_name = settings.AI_PROVIDER
    provider_fn = PROVIDERS.get(provider_name, _verify_mock)

    logger.info("Regenerating content for '%s'", article.title[:50])

    try:
        result = provider_fn(article.title, article.content)
        if result.description:
            article.content = f"<p>{result.description}</p>"
            article.summary = result.description[:300]
        if result.key_points:
            article.key_points = result.key_points
    except Exception as e:
        logger.error("Content generation failed: %s", e)

    if provider_name == "alibaba" and settings.ALIBABA_API_KEY:
        try:
            new_images = _generate_images_alibaba(article.title, article.category)
            if new_images:
                article.images = new_images
        except Exception as e:
            logger.error("Image generation failed: %s", e)

    article.save()
