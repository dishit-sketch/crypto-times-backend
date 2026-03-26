"""
reset_twitter_stream.py

Deletes all Twitter filtered stream rules via the API.
This force-disconnects any active stream connections and clears the slate
so the next deploy can create fresh rules and reconnect cleanly.

Usage:
    python reset_twitter_stream.py
    TWITTER_BEARER_TOKEN=xxx python reset_twitter_stream.py
"""

import os
import sys
import json
import httpx

TWITTER_API_BASE = "https://api.twitter.com/2"
RULES_URL = f"{TWITTER_API_BASE}/tweets/search/stream/rules"


def get_token() -> str:
    # Try env directly, then fall back to Django settings
    token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not token:
        try:
            import django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_times.settings")
            django.setup()
            from django.conf import settings
            token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
        except Exception:
            pass
    return token


def main():
    token = get_token()
    if not token:
        print("ERROR: TWITTER_BEARER_TOKEN not found in env or Django settings.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. GET current rules
    print("Fetching current stream rules...")
    r = httpx.get(RULES_URL, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"ERROR fetching rules: HTTP {r.status_code}")
        print(r.text[:500])
        sys.exit(1)

    body = r.json()
    rules = body.get("data") or []
    meta = body.get("meta", {})

    if not rules:
        print("No stream rules found — stream is already clean.")
        return

    print(f"Found {len(rules)} rule(s):")
    for rule in rules:
        print(f"  [{rule['id']}] {rule.get('value', '')}  tag={rule.get('tag', '')}")

    # 2. DELETE all rules
    ids = [rule["id"] for rule in rules]
    print(f"\nDeleting {len(ids)} rule(s)...")
    r = httpx.post(
        RULES_URL,
        headers=headers,
        json={"delete": {"ids": ids}},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"ERROR deleting rules: HTTP {r.status_code}")
        print(r.text[:500])
        sys.exit(1)

    result = r.json()
    summary = result.get("meta", {}).get("summary", {})
    deleted = summary.get("deleted", len(ids))
    not_deleted = summary.get("not_deleted", 0)

    print(f"Done. Deleted: {deleted}  Not deleted: {not_deleted}")
    print("\nStream rules cleared. Any active stream connections will now receive no tweets.")
    print("The next Railway deploy will create fresh rules and reconnect cleanly.")


if __name__ == "__main__":
    main()
