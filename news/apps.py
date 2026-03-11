import os
from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"
    verbose_name = "News & Verification"

    def ready(self):
        # Only start scheduler in the main process, not in migrate/collectstatic
        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("RUN_MAIN"):
            try:
                from news.scheduler import start
                start()
            except Exception as e:
                print(f"Scheduler start failed: {e}")
