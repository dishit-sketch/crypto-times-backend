import os
import threading
from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"
    verbose_name = "CryptoTimes News Engine"

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            # Run in background thread so it doesn't block server startup
            thread = threading.Thread(target=self._background_init, daemon=True)
            thread.start()

    def _background_init(self):
        import time
        time.sleep(5)  # Wait for server to fully start

        try:
            self._auto_seed_sources()
        except Exception as e:
            print(f"[CryptoTimes] Auto-seed failed: {e}")

        try:
            from news.scheduler import start
            start()
        except Exception as e:
            print(f"[CryptoTimes] Scheduler failed: {e}")

        try:
            from news.scrapers.twitter_stream import start_stream
            start_stream()
        except Exception as e:
            print(f"[CryptoTimes] Twitter stream failed: {e}")

    def _auto_seed_sources(self):
        from news.models import Source
        from news.sources_list import STARTER_SOURCES

        current_count = Source.objects.count()
        if current_count >= 50:
            return

        print(f"[CryptoTimes] Seeding sources...")
        count = 0
        for data in STARTER_SOURCES:
            _, created = Source.objects.get_or_create(
                url=data["url"],
                defaults=data,
            )
            if created:
                count += 1
        print(f"[CryptoTimes] Seeded {count} sources.")