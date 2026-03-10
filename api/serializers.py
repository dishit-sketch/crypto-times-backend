"""
Serializers for The Crypto Times API.
"""

from rest_framework import serializers
from news.models import Source, NewsArticle, VerificationLog


# ── Source ──────────────────────────────────────────────────
class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            "id",
            "name",
            "type",
            "url",
            "logo",
            "description",
            "reliability_score",
            "created_at",
        ]


class SourceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ["name", "type", "url", "logo", "description", "reliability_score", "is_active"]

    def validate_url(self, value):
        if Source.objects.filter(url=value).exists():
            raise serializers.ValidationError("A source with this URL already exists.")
        return value


# ── VerificationLog ─────────────────────────────────────────
class VerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationLog
        fields = ["id", "verdict", "confidence_score", "explanation", "provider", "created_at"]


# ── NewsArticle ─────────────────────────────────────────────
class NewsArticleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""

    source_name = serializers.CharField(source="source.name", read_only=True)
    source_logo = serializers.CharField(source="source.logo", read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "title",
            "summary",
            "images",
            "source_name",
            "source_logo",
            "ai_verdict",
            "confidence_score",
            "is_breaking",
            "category",
            "tags",
            "published_at",
            "created_at",
        ]


class NewsArticleDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail endpoint."""

    source_name = serializers.CharField(source="source.name", read_only=True)
    source_logo = serializers.CharField(source="source.logo", read_only=True)
    source_url = serializers.CharField(source="source.url", read_only=True)
    verification_logs = VerificationLogSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "images",
            "source_name",
            "source_logo",
            "source_url",
            "original_url",
            "author",
            "ai_verdict",
            "confidence_score",
            "status",
            "is_breaking",
            "category",
            "tags",
            "verification_logs",
            "published_at",
            "created_at",
            "updated_at",
        ]


# ── Admin Action Serializers ────────────────────────────────
class ArticleActionSerializer(serializers.Serializer):
    article_id = serializers.UUIDField()


class ArticleEditSerializer(serializers.Serializer):
    article_id = serializers.UUIDField()
    title = serializers.CharField(max_length=500, required=False)
    summary = serializers.CharField(required=False)
    content = serializers.CharField(required=False)
    category = serializers.CharField(max_length=100, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


# ── Paginated Response ──────────────────────────────────────
class PaginatedNewsSerializer(serializers.Serializer):
    """Wraps paginated results to match the frontend NewsListResponse type."""

    articles = NewsArticleListSerializer(many=True, source="results")
    total = serializers.IntegerField(source="count")
    page = serializers.IntegerField()
    pageSize = serializers.IntegerField()
