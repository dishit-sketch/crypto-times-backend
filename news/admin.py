"""
Professional Admin Panel for CryptoTimes.io
With key_points display in list and detail views.
Approve/Reject stays on list page + buttons on detail page.
Source ownership — each admin sees only their own sources and articles.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Source, NewsArticle, VerificationLog, ArticleStatus, AIVerdict


admin.site.site_header = "CryptoTimes.io — News Command Center"
admin.site.site_title = "CryptoTimes Admin"
admin.site.index_title = "Dashboard"


class VerificationLogInline(admin.TabularInline):
    model = VerificationLog
    extra = 0
    readonly_fields = ("verdict", "confidence_score", "explanation", "provider", "created_at")
    can_delete = False
    max_num = 5

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type_badge", "owner_display", "reliability_bar", "article_count", "is_active", "last_fetched_display")
    list_filter = ("type", "is_active", "owner")
    search_fields = ("name", "url", "description")
    list_editable = ("is_active",)
    list_per_page = 50
    readonly_fields = ("id", "created_at", "updated_at", "last_fetched_at")

    fieldsets = (
        ("Source Info", {"fields": ("id", "name", "type", "url", "logo", "description")}),
        ("Ownership", {"fields": ("owner",)}),
        ("Settings", {"fields": ("is_active", "reliability_score")}),
        ("Timestamps", {"fields": ("last_fetched_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(_article_count=Count("articles"))
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(owner=request.user) | Q(owner__isnull=True))

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and 'owner' in form.base_fields:
            form.base_fields['owner'].disabled = True
        return form

    @admin.display(description="Owner")
    def owner_display(self, obj):
        if not obj.owner:
            return format_html('<span style="color:#888;font-size:11px;">Shared</span>')
        return format_html(
            '<span style="color:#f7931a;font-size:11px;font-weight:600;">{}</span>',
            obj.owner.username,
        )

    @admin.display(description="Type")
    def type_badge(self, obj):
        colors = {"twitter": "#1DA1F2", "rss": "#ee802f", "website": "#f7931a"}
        icons = {"twitter": "X", "rss": "R", "website": "W"}
        color = colors.get(obj.type, "#999")
        icon = icons.get(obj.type, "?")
        return format_html(
            '<span style="background:{};color:#fff;padding:4px 12px;border-radius:12px;font-size:11px;font-weight:600;">{} {}</span>',
            color, icon, obj.get_type_display(),
        )

    @admin.display(description="Reliability", ordering="reliability_score")
    def reliability_bar(self, obj):
        score = obj.reliability_score
        color = "#00d395" if score >= 80 else "#f0c040" if score >= 50 else "#ff4757"
        score_str = f"{score}"
        return format_html(
            '<div style="width:100px;height:8px;background:#1a1a2e;border-radius:4px;overflow:hidden;">'
            '<div style="width:{}px;height:100%;background:{};border-radius:4px;"></div>'
            '</div><span style="font-size:11px;color:{};">{}%</span>',
            score, color, color, score_str,
        )

    @admin.display(description="Articles", ordering="_article_count")
    def article_count(self, obj):
        return format_html(
            '<span style="background:#1a1a2e;color:#e8eaed;padding:3px 10px;border-radius:8px;font-size:12px;">{}</span>',
            obj._article_count,
        )

    @admin.display(description="Last Fetched")
    def last_fetched_display(self, obj):
        if not obj.last_fetched_at:
            return format_html('<span style="color:#666;">Never</span>')
        diff = timezone.now() - obj.last_fetched_at
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            return format_html('<span style="color:#00d395;">{}m ago</span>', mins)
        elif mins < 1440:
            return format_html('<span style="color:#f0c040;">{}h ago</span>', mins // 60)
        else:
            return format_html('<span style="color:#ff4757;">{}d ago</span>', mins // 1440)


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail_preview",
        "title_with_source",
        "key_points_preview",
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
        "images_gallery", "key_points_display", "moderation_buttons",
        "original_url_link",
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
            "fields": ("id", "title", "summary", "content", "original_url", "original_url_link"),
            "classes": ("wide",),
        }),
        ("Key Points", {
            "fields": ("key_points", "key_points_display"),
        }),
        ("Source and Author", {
            "fields": ("source", "author", "external_id"),
        }),
        ("Images", {
            "fields": ("images", "images_gallery"),
        }),
        ("AI Verification", {
            "fields": ("ai_verdict", "confidence_score"),
        }),
        ("Moderation", {
            "fields": ("status", "is_breaking", "moderation_buttons"),
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(source__owner=request.user) | Q(source__owner__isnull=True)
        )

    def get_urls(self):
        from django.urls import path
        custom_urls = [
            path(
                '<path:object_id>/quick-approve/',
                self.admin_site.admin_view(self.quick_approve_view),
                name='newsarticle-quick-approve',
            ),
            path(
                '<path:object_id>/quick-reject/',
                self.admin_site.admin_view(self.quick_reject_view),
                name='newsarticle-quick-reject',
            ),
        ]
        return custom_urls + super().get_urls()

    def quick_approve_view(self, request, object_id):
        article = self.get_object(request, object_id)
        if article and article.status == ArticleStatus.PENDING:
            article.approve()
            self.message_user(request, f"✅ Approved: {article.title[:50]}")

        referer = request.META.get('HTTP_REFERER', '')
        if 'change' in referer and str(object_id) in referer:
            return HttpResponseRedirect(reverse('admin:news_newsarticle_changelist'))
        elif referer and 'newsarticle' in referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('admin:news_newsarticle_changelist'))

    def quick_reject_view(self, request, object_id):
        article = self.get_object(request, object_id)
        if article and article.status == ArticleStatus.PENDING:
            article.reject()
            self.message_user(request, f"❌ Rejected: {article.title[:50]}")

        referer = request.META.get('HTTP_REFERER', '')
        if 'change' in referer and str(object_id) in referer:
            return HttpResponseRedirect(reverse('admin:news_newsarticle_changelist'))
        elif referer and 'newsarticle' in referer:
            return HttpResponseRedirect(referer)
        else:
            return HttpResponseRedirect(reverse('admin:news_newsarticle_changelist'))

    @admin.display(description="")
    def thumbnail_preview(self, obj):
        if obj.images and len(obj.images) > 0:
            return format_html(
                '<img src="{}" style="width:60px;height:40px;object-fit:cover;border-radius:6px;border:1px solid #2a2a3e;" />',
                obj.images[0],
            )
        return format_html(
            '<div style="width:60px;height:40px;background:#1a1a2e;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#555;font-size:18px;">N</div>'
        )

    @admin.display(description="Article", ordering="title")
    def title_with_source(self, obj):
        title = obj.title[:60] + ("..." if len(obj.title) > 60 else "")
        source_name = obj.source.name if obj.source else "Unknown"
        return format_html(
            '<div style="max-width:300px;">'
            '<div style="font-weight:600;color:#e8eaed;line-height:1.3;">{}</div>'
            '<div style="font-size:11px;color:#888;margin-top:2px;">{}</div>'
            '</div>',
            title, source_name,
        )

    @admin.display(description="Key Points")
    def key_points_preview(self, obj):
        if not obj.key_points or not isinstance(obj.key_points, list):
            return format_html('<span style="color:#555;">—</span>')
        html = '<div style="max-width:250px;">'
        for i, kp in enumerate(obj.key_points[:3], 1):
            short = str(kp)[:60] + ("..." if len(str(kp)) > 60 else "")
            html += f'<div style="font-size:10px;color:#9aa0ab;line-height:1.4;margin-bottom:2px;">{i}. {short}</div>'
        html += '</div>'
        return format_html(html)

    @admin.display(description="Key Points (Full)")
    def key_points_display(self, obj):
        if not obj.key_points or not isinstance(obj.key_points, list):
            return format_html('<span style="color:#666;">No key points generated yet. Use "Re-verify with AI" to generate.</span>')
        html = '<div style="background:#0d1117;border:1px solid #1a2744;border-radius:10px;padding:16px;max-width:600px;">'
        html += '<div style="font-size:12px;font-weight:700;color:#f7931a;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Key Takeaways</div>'
        for i, kp in enumerate(obj.key_points[:3], 1):
            html += (
                f'<div style="display:flex;gap:10px;margin-bottom:10px;">'
                f'<div style="background:#f7931a;color:#000;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;">{i}</div>'
                f'<div style="font-size:13px;color:#e8eaed;line-height:1.5;">{kp}</div>'
                f'</div>'
            )
        html += '</div>'
        return format_html(html)

    @admin.display(description="Verdict", ordering="ai_verdict")
    def verdict_badge(self, obj):
        colors = {"REAL": "#00d395", "FAKE": "#ff4757", "UNCERTAIN": "#f0c040"}
        icons = {"REAL": "V", "FAKE": "X", "UNCERTAIN": "?"}
        bg = colors.get(obj.ai_verdict, "#999")
        icon = icons.get(obj.ai_verdict, "?")
        return format_html(
            '<span style="background:{};color:#000;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;">{} {}</span>',
            bg, icon, obj.ai_verdict,
        )

    @admin.display(description="Confidence", ordering="confidence_score")
    def confidence_bar(self, obj):
        score = obj.confidence_score
        color = "#00d395" if score >= 80 else "#f0c040" if score >= 50 else "#ff4757"
        score_str = f"{score:.0f}"
        return format_html(
            '<div style="display:flex;align-items:center;gap:6px;">'
            '<div style="width:60px;height:6px;background:#1a1a2e;border-radius:3px;overflow:hidden;">'
            '<div style="width:{}px;height:100%;background:{};border-radius:3px;"></div>'
            '</div>'
            '<span style="font-size:12px;font-weight:600;color:{};">{}%</span>'
            '</div>',
            min(int(score * 0.6), 60), color, color, score_str,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        config = {"pending": ("#f0c040", "P"), "approved": ("#00d395", "A"), "rejected": ("#ff4757", "R")}
        bg, icon = config.get(obj.status, ("#999", "?"))
        return format_html(
            '<span style="background:{};color:#000;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:600;">{} {}</span>',
            bg, icon, obj.get_status_display(),
        )

    @admin.display(description="BRK", boolean=True, ordering="is_breaking")
    def breaking_icon(self, obj):
        return obj.is_breaking

    @admin.display(description="Time", ordering="created_at")
    def time_display(self, obj):
        diff = timezone.now() - obj.created_at
        mins = int(diff.total_seconds() / 60)
        if mins < 60:
            return format_html('<span style="color:#00d395;">{}m</span>', mins)
        elif mins < 1440:
            return format_html('<span style="color:#e8eaed;">{}h</span>', mins // 60)
        else:
            return format_html('<span style="color:#888;">{}d</span>', mins // 1440)

    @admin.display(description="Actions")
    def quick_actions(self, obj):
        if obj.status == ArticleStatus.PENDING:
            approve_url = reverse('admin:newsarticle-quick-approve', args=[obj.pk])
            reject_url = reverse('admin:newsarticle-quick-reject', args=[obj.pk])
            return format_html(
                '<a href="{}" '
                'style="background:#00d395;color:#000;padding:4px 10px;border-radius:6px;'
                'text-decoration:none;font-size:11px;font-weight:600;margin-right:4px;"'
                '>Approve</a>'
                '<a href="{}" '
                'style="background:#ff4757;color:#fff;padding:4px 10px;border-radius:6px;'
                'text-decoration:none;font-size:11px;font-weight:600;"'
                '>Reject</a>',
                approve_url, reject_url,
            )
        elif obj.status == ArticleStatus.APPROVED:
            return format_html('<span style="color:#00d395;font-size:11px;font-weight:600;">✅ Live</span>')
        elif obj.status == ArticleStatus.REJECTED:
            return format_html('<span style="color:#ff4757;font-size:11px;font-weight:600;">❌ Rejected</span>')
        return format_html('<span style="color:#555;">—</span>')

    @admin.display(description="Quick Moderation")
    def moderation_buttons(self, obj):
        approve_url = reverse('admin:newsarticle-quick-approve', args=[obj.pk])
        reject_url = reverse('admin:newsarticle-quick-reject', args=[obj.pk])

        if obj.status == ArticleStatus.PENDING:
            return format_html(
                '<div style="display:flex;gap:12px;margin:10px 0;">'
                '<a href="{}" style="background:#00d395;color:#000;padding:10px 30px;'
                'border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;'
                'display:inline-block;text-align:center;min-width:120px;'
                'box-shadow:0 2px 8px rgba(0,211,149,0.3);"'
                '>✅ APPROVE</a>'
                '<a href="{}" style="background:#ff4757;color:#fff;padding:10px 30px;'
                'border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;'
                'display:inline-block;text-align:center;min-width:120px;'
                'box-shadow:0 2px 8px rgba(255,71,87,0.3);"'
                '>❌ REJECT</a>'
                '</div>',
                approve_url, reject_url,
            )
        elif obj.status == ArticleStatus.APPROVED:
            return format_html(
                '<div style="display:flex;gap:12px;align-items:center;margin:10px 0;">'
                '<span style="background:#00d395;color:#000;padding:10px 30px;'
                'border-radius:8px;font-size:14px;font-weight:700;'
                'display:inline-block;">✅ APPROVED — LIVE</span>'
                '<a href="{}" style="background:#ff4757;color:#fff;padding:10px 30px;'
                'border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;'
                'display:inline-block;text-align:center;min-width:120px;'
                'box-shadow:0 2px 8px rgba(255,71,87,0.3);"'
                '>❌ REJECT</a>'
                '</div>',
                reject_url,
            )
        elif obj.status == ArticleStatus.REJECTED:
            return format_html(
                '<div style="display:flex;gap:12px;align-items:center;margin:10px 0;">'
                '<a href="{}" style="background:#00d395;color:#000;padding:10px 30px;'
                'border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;'
                'display:inline-block;text-align:center;min-width:120px;'
                'box-shadow:0 2px 8px rgba(0,211,149,0.3);"'
                '>✅ APPROVE</a>'
                '<span style="background:#ff4757;color:#fff;padding:10px 30px;'
                'border-radius:8px;font-size:14px;font-weight:700;'
                'display:inline-block;">❌ REJECTED</span>'
                '</div>',
                approve_url,
            )
        return format_html('<span style="color:#555;">—</span>')

    @admin.display(description="Images")
    def images_gallery(self, obj):
        if not obj.images:
            return format_html('<span style="color:#666;">No images</span>')
        html = '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        for url in obj.images[:6]:
            html += f'<img src="{url}" style="height:100px;width:150px;object-fit:cover;border-radius:8px;border:2px solid #2a2a3e;" />'
        html += '</div>'
        return format_html(html)

    @admin.display(description="Source Link")
    def original_url_link(self, obj):
        if not obj.original_url:
            return format_html('<span style="color:#666;">No URL</span>')
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer" '
            'style="color:#f7931a;text-decoration:none;font-weight:600;">'
            '🔗 Open Source Article ↗</a>',
            obj.original_url,
        )

    @admin.action(description="Approve selected articles")
    def approve_selected(self, request, queryset):
        count = 0
        for article in queryset.filter(status=ArticleStatus.PENDING):
            article.approve()
            count += 1
        self.message_user(request, f"{count} article(s) approved.")

    @admin.action(description="Reject selected articles")
    def reject_selected(self, request, queryset):
        count = queryset.update(status=ArticleStatus.REJECTED, is_breaking=False)
        self.message_user(request, f"{count} article(s) rejected.")

    @admin.action(description="Auto-approve all REAL with high confidence")
    def approve_all_real(self, request, queryset):
        count = 0
        for article in queryset.filter(status=ArticleStatus.PENDING, ai_verdict=AIVerdict.REAL, confidence_score__gt=80):
            article.approve()
            count += 1
        self.message_user(request, f"Auto-approved {count} REAL article(s).")

    @admin.action(description="Re-verify with AI")
    def re_verify_selected(self, request, queryset):
        from news.ai.verifier import verify_article
        count = 0
        for article in queryset:
            try:
                verify_article(article)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error: {article.title[:40]}: {e}", level="error")
        self.message_user(request, f"{count} article(s) re-verified.")

    @admin.action(description="Regenerate content and images with AI")
    def regenerate_content_selected(self, request, queryset):
        from news.ai.verifier import generate_article_content
        count = 0
        for article in queryset:
            try:
                generate_article_content(article)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error: {article.title[:40]}: {e}", level="error")
        self.message_user(request, f"{count} article(s) regenerated.")


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ("article_short", "verdict_badge", "confidence_score", "provider", "created_at")
    list_filter = ("verdict", "provider")
    list_per_page = 50
    readonly_fields = ("id", "article", "verdict", "confidence_score", "explanation", "provider", "raw_response", "created_at")

    @admin.display(description="Article")
    def article_short(self, obj):
        return obj.article.title[:55]

    @admin.display(description="Verdict")
    def verdict_badge(self, obj):
        colors = {"REAL": "#00d395", "FAKE": "#ff4757", "UNCERTAIN": "#f0c040"}
        bg = colors.get(obj.verdict, "#999")
        return format_html(
            '<span style="background:{};color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            bg, obj.verdict,
        )

    def has_add_permission(self, request):
        return False
