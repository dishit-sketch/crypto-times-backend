"""ASGI config for The Crypto Times."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_times.settings")
application = get_asgi_application()
