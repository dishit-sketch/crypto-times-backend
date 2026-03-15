"""
URL routing for The Crypto Times API.
"""

from django.urls import path
from api import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────
    path("news/latest", views.LatestNewsView.as_view(), name="news-latest"),
    path("news/breaking", views.breaking_news, name="news-breaking"),
    path("news/<uuid:id>", views.NewsDetailView.as_view(), name="news-detail"),
    path("sources", views.SourceListView.as_view(), name="sources-list"),

    # ── Admin ───────────────────────────────────────────────
    path("admin/approve-news", views.approve_news, name="admin-approve"),
    path("admin/reject-news", views.reject_news, name="admin-reject"),
    path("admin/edit-news", views.edit_news, name="admin-edit"),
    path("admin/add-source", views.add_source, name="admin-add-source"),
    path("admin/remove-source/<uuid:source_id>", views.remove_source, name="admin-remove-source"),
    path("admin/pending", views.PendingArticlesView.as_view(), name="admin-pending"),
    path("admin/recent-articles", views.recent_articles, name="admin-recent-articles"),
]
