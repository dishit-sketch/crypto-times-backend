"""
Professional Admin Panel for CryptoTimes.io
Features:
  - Dashboard with stats
  - Quick approve/reject buttons per row
  - Batch actions
  - Image previews
  - Color-coded verdicts and statuses
  - One-click AI re-verify + regenerate
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from .models import Source, NewsArticle, VerificationLog, ArticleStatus, AIVerdict


# ── Admin Site Branding ─────────────────────────────────────
admin.site.site_header = "CryptoTimes.io — News Command Center"
admin.site.site_title = "CryptoTimes Admin"
admin.site.index_title = "Dashboard"


# ── Inlines ─────────────────────────────────────────────────
class VerificationLogInline(admin.TabularInline):
    model = VerificationLog
    extra = 0
    readonly_fields = ("verdict", "confidence_score", "explanation", "provider", "created_at")
    can_delete = False
    max_num = 5

    def has_add_permission(self, request, obj=None):
        return False


# ══════════════════════════════════════════════════════════
# SOURCE ADMIN
# ══════════════════════════════════════════════════════════
@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type_badge",
        "reliability_bar",
        "article_count",
        "is_active",
        "last_fetched_display",
    )
    list_filter = ("type", "is_active")
    search_fields = ("name", "url", "description")
    list_editable = ("is_active",)
    list_per_page = 50
    readonly_fields = ("id", "created_at", "updated_at", "last_fetched_at")

    fieldsets = (
        ("Source Info", {"fields": ("id", "name", "type", "url", "logo", "description")}),
        ("Settings", {"fields": ("is_active", "reliability_score")}),
        ("Timestamps", {"fields": ("last_fetched_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _article_count=Count("articles"),
        )

    @admin.display(description="Type")
    def type_badge(self, obj):
        colors = {"twitter": "#1DA1F2", "rss": "#ee802f", "website": "#f7931a"}
        icons = {"twitter": "𝕏", "rss": "◉", "website": "◎"}
        color = colors.get(obj.type, "#999")
        icon = icons.get(obj.type, "●")
        return format_html(
            '<span style="background:{};color:#fff;padding:4px 12px;border-radius:12px;'
            'font-size:11px;font-weight:600;">{} {}</span>',
            color, icon, obj.get_type_display(),
        )

    @admin.display(description="Reliability", ordering="reliability_score")
    def reliability_bar(self, obj):
        score = obj.reliability_score
        color = "#00d395" if score >= 80 else "#f0c040" if score >= 50 else "#ff4757"
        return format_html(
            '<div style="width:100px;height:8px;background:#1a1a2e;border-radius:4px;overflow:hidden;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:4px;"></div>'
            '</div>'
            '<span style="font-size:11px;color:{};">{}</span>',
            score, color, color, f"{score}%",
        )

    @admin.display(description="Articles", ordering="_article_count")
    def article_count(self, obj):
        return format_html(
            '<span style="background:#1a1a2e;color:#e8eaed;padding:3px 10px;'
            'border-radius:8px;font-size:12px;font-weight:500;">{}</span>',
            obj._article_count,
        )

    @admin.display(description="Last Fetched")
    def last_fetched_display(self, obj):
        if not obj.last_fetched_at:
            return format_html('<span style="color:#666;">Never</span>')
        diff = timezone.now() - obj.last_fetched_at
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            text = f"{mins}m ago"
            color = "#00d395"
        elif mins < 1440:
            text = f"{mins // 60}h ago"
            color = "#f0c040"
        else:
            text = f"{mins // 1440}d ago"
            color = "#ff4757"
        return format_html('<span style="color:{};">{}</span>', color, text)


# ══════════════════════════════════════════════════════════
# NEWS ARTICLE ADMIN
# ══════════════════════════════════════════════════════════
@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail_preview",
        "title_with_source",
        "verdict_badge",
        "confidence_bar",
        "status_badge",
        "breaking_icon",
        "time_display",
        "quick_actions",
    )
    list_filter = ("status", "ai_verdict", "is_breaking", "category", "source")
    search_fields = ("title", "summary", "content", "tags")
    list_per_page = 30
    list_display_links = ("title_with_source",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "id", "ai_verdict", "confidence_score", "is_breaking",
        "created_at", "updated_at", "published_at", "external_id",
        "images_gallery",
    )
    actions = [
        "approve_selected",
        "reject_selected",
        "re_verify_selected",
        "regenerate_content_selected",
        "approve_all_real",
    ]
    inlines = [VerificationLogInline]

    fieldsets = (
        ("Article", {
            "fields": ("id", "title", "summary", "content", "original_url"),
            "classes": ("wide",),
        }),
        ("Source & Author", {
            "fields": ("source", "author", "external_id"),
        }),
        ("Images", {
            "fields": ("images", "images_gallery"),
        }),
        ("AI Verification", {
            "fields": ("ai_verdict", "confidence_score"),
        }),
        ("Moderation", {
            "fields": ("status", "is_breaking"),
        }),
        ("Metadata", {
            "fields": ("category", "tags"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "published_at"),
            "classes": ("collapse",),
        }),
    )

    # ── List Display Methods ────────────────────────────────

    @admin.display(description="")
    def thumbnail_preview(self, obj):
        if obj.images and len(obj.images) > 0:
            return format_html(
                '<img src="{}" style="width:60px;height:40px;object-fit:cover;'
                'border-radius:6px;border:1px solid #2a2a3e;" />',
                obj.images[0],
            )
        return format_html(
            '<div style="width:60px;height:40px;background:#1a1a2e;border-radius:6px;'
            'display:flex;align-items:center;justify-content:center;color:#555;font-size:10px;">No img</div>'
        )

    @admin.display(description="Article", ordering="title")
    def title_with_source(self, obj):
        title = obj.title[:65] + ("…" if len(obj.title) > 65 else "")
        source_name = obj.source.name if obj.source else "Unknown"
        return format_html(
            '<div style="max-width:350px;">'
            '<div style="font-weight:600;color:#e8eaed;line-height:1.3;">{}</div>'
            '<div style="font-size:11px;color:#888;margin-top:2px;">{}</div>'
            '</div>',
            title, source_name,
        )

    @admin.display(description="Verdict", ordering="ai_verdict")
    def verdict_badge(self, obj):
        colors = {"REAL": "#00d395", "FAKE": "#ff4757", "UNCERTAIN": "#f0c040"}
        icons = {"REAL": "✓", "FAKE": "✗", "UNCERTAIN": "?"}
        bg = colors.get(obj.ai_verdict, "#999")
        icon = icons.get(obj.ai_verdict, "?")
        return format_html(
            '<span style="background:{bg};color:#000;padding:4px 10px;border-radius:12px;'
            'font-size:11px;font-weight:700;">{icon} {verdict}</span>',
            bg=bg, icon=icon, verdict=obj.ai_verdict,
        )

    @admin.display(description="Confidence", ordering="confidence_score")
    def confidence_bar(self, obj):
        score = obj.confidence_score
        color = "#00d395" if score >= 80 else "#f0c040" if score >= 50 else "#ff4757"
        score_str = f"{score:.0f}"
        return format_html(
            '<div style="display:flex;align-items:center;gap:6px;">'
            '<div style="width:60px;height:6px;background:#1a1a2e;border-radius:3px;overflow:hidden;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:3px;"></div>'
            '</div>'
            '<span style="font-size:12px;font-weight:600;color:{};">{}%</span>'
            '</div>',
            score, color, color, score_str,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        config = {
            "pending": ("#f0c040", "⏳"),
            "approved": ("#00d395", "✓"),
            "rejected": ("#ff4757", "✗"),
        }
        bg, icon = config.get(obj.status, ("#999", "?"))
        return format_html(
            '<span style="background:{bg};color:#000;padding:4px 10px;border-radius:12px;'
            'font-size:11px;font-weight:600;">{icon} {label}</span>',
            bg=bg, icon=icon, label=obj.get_status_display(),
        )

    @admin.display(description="🔥", boolean=True, ordering="is_breaking")
    def breaking_icon(self, obj):
        return obj.is_breaking

    @admin.display(description="Time", ordering="created_at")
    def time_display(self, obj):
        diff = timezone.now() - obj.created_at
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            return format_html('<span style="color:#00d395;">{} min ago</span>', mins)
        elif mins < 1440:
            return format_html('<span style="color:#e8eaed;">{} hrs ago</span>', mins // 60)
        else:
            return format_html('<span style="color:#888;">{} days ago</span>', mins // 1440)

    @admin.display(description="Actions")
    def quick_actions(self, obj):
        if obj.status == ArticleStatus.PENDING:
            return format_html(
                '<a href="/admin/news/newsarticle/{}/change/?_approve=1" '
                'style="background:#00d395;color:#000;padding:4px 10px;border-radius:6px;'
                'text-decoration:none;font-size:11px;font-weight:600;margin-right:4px;">Approve</a>'
                '<a href="/admin/news/newsarticle/{}/change/?_reject=1" '
                'style="background:#ff4757;color:#fff;padding:4px 10px;border-radius:6px;'
                'text-decoration:none;font-size:11px;font-weight:600;">Reject</a>',
                obj.pk, obj.pk,
            )
        return format_html('<span style="color:#555;">—</span>')

    @admin.display(description="Images")
    def images_gallery(self, obj):
        if not obj.images:
            return format_html('<span style="color:#666;">No images attached</span>')
        html = '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        for i, url in enumerate(obj.images[:6]):
            html += (
                f'<img src="{url}" style="height:100px;width:150px;object-fit:cover;'
                f'border-radius:8px;border:2px solid #2a2a3e;" />'
            )
        html += '</div>'
        return format_html(html)

    # ── Quick approve/reject from change view ───────────────
    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.GET.get("_approve") == "1":
            article = self.get_object(request, object_id)
            if article and article.status == ArticleStatus.PENDING:
                article.approve()
                self.message_user(request, f"✅ Approved: {article.title[:50]}")
        elif request.GET.get("_reject") == "1":
            article = self.get_object(request, object_id)
            if article and article.status == ArticleStatus.PENDING:
                article.reject()
                self.message_user(request, f"❌ Rejected: {article.title[:50]}")
        return super().change_view(request, object_id, form_url, extra_context)

    # ── Bulk Actions ────────────────────────────────────────

    @admin.action(description="✅ Approve selected articles")
    def approve_selected(self, request, queryset):
        count = 0
        for article in queryset.filter(status=ArticleStatus.PENDING):
            article.approve()
            count += 1
        self.message_user(request, f"✅ {count} article(s) approved.")

    @admin.action(description="❌ Reject selected articles")
    def reject_selected(self, request, queryset):
        count = queryset.update(status=ArticleStatus.REJECTED, is_breaking=False)
        self.message_user(request, f"❌ {count} article(s) rejected.")

    @admin.action(description="✅ Auto-approve all REAL (confidence > 80%)")
    def approve_all_real(self, request, queryset):
        count = 0
        for article in queryset.filter(
            status=ArticleStatus.PENDING,
            ai_verdict=AIVerdict.REAL,
            confidence_score__gt=80,
        ):
            article.approve()
            count += 1
        self.message_user(request, f"✅ Auto-approved {count} REAL article(s) with >80% confidence.")

    @admin.action(description="🤖 Re-verify + regenerate with AI")
    def re_verify_selected(self, request, queryset):
        from news.ai.verifier import verify_article

        count = 0
        for article in queryset:
            try:
                verify_article(article)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error: {article.title[:40]}: {e}", level="error")
        self.message_user(request, f"🤖 {count} article(s) re-verified with AI.")

    @admin.action(description="📝 Regenerate content + images with AI")
    def regenerate_content_selected(self, request, queryset):
        from news.ai.verifier import generate_article_content

        count = 0
        for article in queryset:
            try:
                generate_article_content(article)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error: {article.title[:40]}: {e}", level="error")
        self.message_user(request, f"📝 {count} article(s) regenerated with AI content + images.")


# ══════════════════════════════════════════════════════════
# VERIFICATION LOG ADMIN
# ══════════════════════════════════════════════════════════
@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ("article_short", "verdict_badge", "confidence_score", "provider", "created_at")
    list_filter = ("verdict", "provider")
    list_per_page = 50
    readonly_fields = (
        "id", "article", "verdict", "confidence_score",
        "explanation", "provider", "raw_response", "created_at",
    )

    @admin.display(description="Article")
    def article_short(self, obj):
        return obj.article.title[:55] + ("…" if len(obj.article.title) > 55 else "")

    @admin.display(description="Verdict")
    def verdict_badge(self, obj):
        colors = {"REAL": "#00d395", "FAKE": "#ff4757", "UNCERTAIN": "#f0c040"}
        bg = colors.get(obj.verdict, "#999")
        return format_html(
            '<span style="background:{};color:#000;padding:3px 8px;border-radius:10px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, obj.verdict,
        )

    def has_add_permission(self, request):
        return False
