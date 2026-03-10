"""
Database models for The Crypto Times news platform.
"""

import uuid
from django.db import models
from django.utils import timezone


# ── Choices ─────────────────────────────────────────────────
class SourceType(models.TextChoices):
    TWITTER = "twitter", "X (Twitter)"
    RSS = "rss", "RSS Feed"
    WEBSITE = "website", "Website"


class AIVerdict(models.TextChoices):
    REAL = "REAL", "Real"
    FAKE = "FAKE", "Fake"
    UNCERTAIN = "UNCERTAIN", "Uncertain"


class ArticleStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


# ── Source ──────────────────────────────────────────────────
class Source(models.Model):
    """A monitored news source (Twitter account, RSS feed, or website)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=SourceType.choices)
    url = models.URLField(max_length=500)
    logo = models.URLField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, help_text="Inactive sources are skipped during fetching.")
    reliability_score = models.IntegerField(
        default=50,
        help_text="0–100 baseline trust score assigned by admin.",
    )
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Monitored Source"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


# ── NewsArticle ─────────────────────────────────────────────
class NewsArticle(models.Model):
    """A single crypto news article collected and verified by the system."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    summary = models.TextField(help_text="Short AI-generated or extracted summary.")
    content = models.TextField(help_text="Full article body (HTML allowed).")
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    original_url = models.URLField(max_length=700, blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")

    # Images — stored as JSON list of URLs
    images = models.JSONField(
        default=list,
        blank=True,
        help_text='JSON list of image URLs, e.g. ["https://…/a.jpg", "https://…/b.jpg"]',
    )

    # AI verification
    ai_verdict = models.CharField(
        max_length=12,
        choices=AIVerdict.choices,
        default=AIVerdict.UNCERTAIN,
    )
    confidence_score = models.FloatField(
        default=0,
        help_text="AI confidence 0–100.",
    )

    # Human moderation
    status = models.CharField(
        max_length=10,
        choices=ArticleStatus.choices,
        default=ArticleStatus.PENDING,
    )
    is_breaking = models.BooleanField(
        default=False,
        help_text="Marked as breaking when: REAL + confidence > 90 + admin approved.",
    )

    # Metadata
    category = models.CharField(max_length=100, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    external_id = models.CharField(
        max_length=500,
        blank=True,
        default="",
        db_index=True,
        help_text="Unique ID from the original source to prevent duplicates.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when article is approved.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["ai_verdict", "-confidence_score"]),
            models.Index(fields=["is_breaking", "-published_at"]),
        ]

    def __str__(self):
        return self.title[:80]

    def approve(self):
        """Approve the article for public display."""
        self.status = ArticleStatus.APPROVED
        self.published_at = timezone.now()
        # Breaking logic
        if (
            self.ai_verdict == AIVerdict.REAL
            and self.confidence_score > 90
        ):
            self.is_breaking = True
        self.save()

    def reject(self):
        """Reject the article."""
        self.status = ArticleStatus.REJECTED
        self.is_breaking = False
        self.save()


# ── VerificationLog ─────────────────────────────────────────
class VerificationLog(models.Model):
    """Stores AI verification history for each article."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name="verification_logs",
    )
    verdict = models.CharField(max_length=12, choices=AIVerdict.choices)
    confidence_score = models.FloatField(default=0)
    explanation = models.TextField(
        blank=True,
        default="",
        help_text="AI-generated explanation of the verdict.",
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Which AI provider was used (mock / anthropic / openai).",
    )
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full raw AI response for debugging.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Verification Log"

    def __str__(self):
        return f"{self.article.title[:40]} → {self.verdict} ({self.confidence_score}%)"
