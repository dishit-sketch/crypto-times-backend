"""
API views for The Crypto Times.

Public endpoints (no auth):
  GET /api/news/latest     — paginated approved articles
  GET /api/news/breaking   — latest breaking news event
  GET /api/news/{id}       — single article detail
  GET /api/sources         — list monitored sources

Admin endpoints (staff auth):
  POST /api/admin/approve-news
  POST /api/admin/reject-news
  POST /api/admin/edit-news
  POST /api/admin/add-source
  DELETE /api/admin/remove-source/{id}
  GET  /api/admin/pending   — pending articles for moderation
"""

import logging
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from news.models import NewsArticle, Source, ArticleStatus
from api.serializers import (
    NewsArticleListSerializer,
    NewsArticleDetailSerializer,
    SourceSerializer,
    SourceCreateSerializer,
    ArticleActionSerializer,
    ArticleEditSerializer,
    VerificationLogSerializer,
)

logger = logging.getLogger("api")


# ── Pagination ──────────────────────────────────────────────
class NewsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "pageSize"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            "articles": data,
            "total": self.page.paginator.count,
            "page": self.page.number,
            "pageSize": self.get_page_size(self.request),
        })


# ══════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════

class LatestNewsView(generics.ListAPIView):
    """
    GET /api/news/latest
    Returns paginated, approved articles sorted by newest first.
    """
    serializer_class = NewsArticleListSerializer
    pagination_class = NewsPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = NewsArticle.objects.filter(
            status=ArticleStatus.APPROVED,
        ).select_related("source").order_by("-published_at", "-created_at")

        # Optional filters
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)

        verdict = self.request.query_params.get("verdict")
        if verdict:
            qs = qs.filter(ai_verdict=verdict.upper())

        source_id = self.request.query_params.get("source")
        if source_id:
            qs = qs.filter(source_id=source_id)

        return qs


class NewsDetailView(generics.RetrieveAPIView):
    """
    GET /api/news/{id}
    Returns full article detail including verification logs.
    """
    serializer_class = NewsArticleDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        return NewsArticle.objects.filter(
            status=ArticleStatus.APPROVED,
        ).select_related("source").prefetch_related("verification_logs")


class SourceListView(generics.ListAPIView):
    """
    GET /api/sources
    Returns all active monitored sources.
    """
    serializer_class = SourceSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = Source.objects.filter(is_active=True)
        source_type = self.request.query_params.get("type")
        if source_type:
            qs = qs.filter(type=source_type)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"sources": serializer.data})


@api_view(["GET"])
@permission_classes([AllowAny])
def breaking_news(request):
    """
    GET /api/news/breaking
    Returns the most recent breaking news article, or null.
    Supports ?after=<id> param to only return news newer than that ID.
    """
    qs = NewsArticle.objects.filter(
        is_breaking=True,
        status=ArticleStatus.APPROVED,
    ).order_by("-published_at")

    after_id = request.query_params.get("after")
    if after_id:
        try:
            after_article = NewsArticle.objects.get(id=after_id)
            qs = qs.filter(published_at__gt=after_article.published_at)
        except NewsArticle.DoesNotExist:
            pass

    article = qs.first()
    if not article:
        return Response(None)

    return Response({
        "id": str(article.id),
        "headline": article.title,
        "articleId": str(article.id),
        "timestamp": article.published_at.isoformat() if article.published_at else article.created_at.isoformat(),
    })


# ══════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAdminUser])
def approve_news(request):
    """
    POST /api/admin/approve-news
    Body: {"article_id": "<uuid>"}
    """
    serializer = ArticleActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        article = NewsArticle.objects.get(id=serializer.validated_data["article_id"])
    except NewsArticle.DoesNotExist:
        return Response({"error": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

    article.approve()
    logger.info("Article approved by %s: %s", request.user, article.title[:50])

    return Response({
        "status": "approved",
        "is_breaking": article.is_breaking,
        "article_id": str(article.id),
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def reject_news(request):
    """
    POST /api/admin/reject-news
    Body: {"article_id": "<uuid>"}
    """
    serializer = ArticleActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        article = NewsArticle.objects.get(id=serializer.validated_data["article_id"])
    except NewsArticle.DoesNotExist:
        return Response({"error": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

    article.reject()
    logger.info("Article rejected by %s: %s", request.user, article.title[:50])

    return Response({"status": "rejected", "article_id": str(article.id)})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def edit_news(request):
    """
    POST /api/admin/edit-news
    Body: {"article_id": "<uuid>", "title": "...", "summary": "...", ...}
    """
    serializer = ArticleEditSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        article = NewsArticle.objects.get(id=data["article_id"])
    except NewsArticle.DoesNotExist:
        return Response({"error": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

    update_fields = []
    for field in ("title", "summary", "content", "category", "tags"):
        if field in data:
            setattr(article, field, data[field])
            update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        article.save(update_fields=update_fields)
        logger.info("Article edited by %s: %s", request.user, article.title[:50])

    return Response({
        "status": "updated",
        "article_id": str(article.id),
        "updated_fields": update_fields,
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def add_source(request):
    """
    POST /api/admin/add-source
    Body: {"name": "...", "type": "rss|twitter|website", "url": "...", ...}
    """
    serializer = SourceCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    source = serializer.save()
    logger.info("Source added by %s: %s", request.user, source.name)

    return Response(
        SourceSerializer(source).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def remove_source(request, source_id):
    """
    DELETE /api/admin/remove-source/{id}
    """
    try:
        source = Source.objects.get(id=source_id)
    except Source.DoesNotExist:
        return Response({"error": "Source not found."}, status=status.HTTP_404_NOT_FOUND)

    name = source.name
    source.delete()
    logger.info("Source removed by %s: %s", request.user, name)

    return Response({"status": "deleted", "name": name})


class PendingArticlesView(generics.ListAPIView):
    """
    GET /api/admin/pending
    Returns all pending articles for the moderation panel.
    """
    serializer_class = NewsArticleListSerializer
    permission_classes = [IsAdminUser]
    pagination_class = NewsPagination

    def get_queryset(self):
        return NewsArticle.objects.filter(
            status=ArticleStatus.PENDING,
        ).select_related("source").order_by("-created_at")
