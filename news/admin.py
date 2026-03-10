"""
Admin configuration for The Crypto Times moderation panel.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Source, NewsArticle, VerificationLog, ArticleStatus, AIVerdict


# ── Inlines ─────────────────────────────────────────────────
class VerificationLogInline(admin.TabularInline):
    model = VerificationLog
    extra = 0
    readonly_fields = ("verdict", "confidence_score", "explanation", "provider", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ── Source Admin ────────────────────────────────────────────
@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type_badge", "url_link", "is_active", "reliability_score", "last_fetched_at")
    list_filter = ("type", "is_active")
    search_fields = ("name", "url")
    list_editable = ("is_active", "reliability_score")
    readonly_fields = ("id", "created_at", "updated_at", "last_fetched_at")

    fieldsets = (
        (None, {"fields": ("id", "name", "type", "url", "logo", "description")}),
        ("Configuration", {"fields": ("is_active", "reliability_score")}),
        ("Timestamps", {"fields": ("last_fetched_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Type")
    def type_badge(self, obj):
        colors = {"twitter": "#1DA1F2", "rss": "#ee802f", "website": "#f7931a"}
        color = colors.get(obj.type, "#999")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;">{}</span>',
            color,
            obj.get_type_display(),
        )

    @admin.display(description="URL")
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.url, obj.url[:60])


# ── NewsArticle Admin ───────────────────────────────────────
@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title_short",
        "source",
        "verdict_badge",
        "confidence_display",
        "status_badge",
        "is_breaking",
        "created_at",
    )
    list_filter = ("status", "ai_verdict", "is_breaking", "source__type", "source")
    search_fields = ("title", "summary", "content")
    readonly_fields = (
        "id",
        "ai_verdict",
        "confidence_score",
        "is_breaking",
        "created_at",
        "updated_at",
        "published_at",
        "external_id",
        "images_preview",
    )
    actions = ["approve_selected", "reject_selected", "re_verify_selected"]
    inlines = [VerificationLogInline]

    fieldsets = (
        (None, {"fields": ("id", "title", "summary", "content", "original_url")}),
        ("Source", {"fields": ("source", "author", "external_id")}),
        ("Images", {"fields": ("images", "images_preview")}),
        ("AI Verification", {"fields": ("ai_verdict", "confidence_score"), "classes": ("wide",)}),
        ("Moderation", {"fields": ("status", "is_breaking")}),
        ("Metadata", {"fields": ("category", "tags"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "published_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Title")
    def title_short(self, obj):
        return obj.title[:70] + ("…" if len(obj.title) > 70 else "")

    @admin.display(description="AI Verdict")
    def verdict_badge(self, obj):
        colors = {"REAL": "#00d395", "FAKE": "#ff4757", "UNCERTAIN": "#f0c040"}
        bg = colors.get(obj.ai_verdict, "#999")
        return format_html(
            '<span style="background:{};color:#000;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            bg,
            obj.ai_verdict,
        )

    @admin.display(description="Confidence")
    def confidence_display(self, obj):
        try:
            score = float(obj.confidence_score or 0)
        except (TypeError, ValueError):
          score = 0

        color = "#00d395" if score >= 80 else "#f0c040" if score >= 50 else "#ff4757"

        return format_html(
        '<span style="color:{};font-weight:600;">{}%</span>',
        color,
        round(score),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {"pending": "#f0c040", "approved": "#00d395", "rejected": "#ff4757"}
        bg = colors.get(obj.status, "#999")
        return format_html(
            '<span style="background:{};color:#000;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            bg,
            obj.get_status_display(),
        )

    @admin.display(description="Images")
    def images_preview(self, obj):
        if not obj.images:
            return "No images"
        html = ""
        for url in obj.images[:4]:
            html += f'<img src="{url}" style="height:80px;margin:4px;border-radius:6px;object-fit:cover;" />'
        return format_html(html)

    # ── Bulk Actions ────────────────────────────────────────
    @admin.action(description="✅ Approve selected articles")
    def approve_selected(self, request, queryset):
        count = 0
        for article in queryset.filter(status=ArticleStatus.PENDING):
            article.approve()
            count += 1
        self.message_user(request, f"{count} article(s) approved.")

    @admin.action(description="❌ Reject selected articles")
    def reject_selected(self, request, queryset):
        count = queryset.update(
            status=ArticleStatus.REJECTED,
            is_breaking=False,
        )
        self.message_user(request, f"{count} article(s) rejected.")

    @admin.action(description="🔄 Re-verify with AI")
    def re_verify_selected(self, request, queryset):
        from news.ai.verifier import verify_article

        count = 0
        for article in queryset:
            try:
                verify_article(article)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error verifying '{article.title[:40]}': {e}", level="error")
        self.message_user(request, f"{count} article(s) re-verified.")


# ── VerificationLog Admin ───────────────────────────────────
@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ("article_title", "verdict", "confidence_score", "provider", "created_at")
    list_filter = ("verdict", "provider")
    readonly_fields = ("id", "article", "verdict", "confidence_score", "explanation", "provider", "raw_response", "created_at")

    @admin.display(description="Article")
    def article_title(self, obj):
        return obj.article.title[:60]

    def has_add_permission(self, request):
        return False
