import os
from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"
    verbose_name = "CryptoTimes News Engine"

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            try:
                self._auto_seed_sources()
            except Exception as e:
                print(f"[CryptoTimes] Auto-seed failed: {e}")

            try:
                from news.scheduler import start
                start()
            except Exception as e:
                print(f"[CryptoTimes] Scheduler failed: {e}")

    def _auto_seed_sources(self):
        """Auto-add all 100+ sources if database has fewer than 50."""
        from news.models import Source
        from news.sources_list import STARTER_SOURCES

        current_count = Source.objects.count()
        if current_count >= 50:
            return

        print(f"[CryptoTimes] Found {current_count} sources — seeding {len(STARTER_SOURCES)} original sources...")

        count = 0
        for data in STARTER_SOURCES:
            _, created = Source.objects.get_or_create(
                url=data["url"],
                defaults=data,
            )
            if created:
                count += 1

        print(f"[CryptoTimes] Seeded {count} new sources. Total: {Source.objects.count()}")
