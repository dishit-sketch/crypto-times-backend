"""Root URL configuration for The Crypto Times."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "The Crypto Times — Admin"
admin.site.site_title = "Crypto Times Admin"
admin.site.index_title = "News Moderation Dashboard"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("mfa/", include("mfa.urls")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
