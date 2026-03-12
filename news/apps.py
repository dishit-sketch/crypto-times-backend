import os
from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"
    verbose_name = "News & Verification"

    def ready(self):
        # Only run in the main process
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            try:
                self._auto_seed_sources()
            except Exception as e:
                print(f"Auto-seed sources failed: {e}")

            try:
                from news.scheduler import start
                start()
            except Exception as e:
                print(f"Scheduler start failed: {e}")

    def _auto_seed_sources(self):
        """Automatically add default sources if the database is empty."""
        from news.models import Source

        # Only seed if no sources exist yet
        if Source.objects.exists():
            return

        print("[Auto-Seed] No sources found — adding default crypto sources...")

        from news.management.commands.seed_sources import STARTER_SOURCES

        count = 0
        for data in STARTER_SOURCES:
            _, created = Source.objects.get_or_create(
                url=data["url"],
                defaults=data,
            )
            if created:
                count += 1
                print(f"  + {data['name']}")

        print(f"[Auto-Seed] Done — {count} sources added.")
