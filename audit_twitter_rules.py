"""
audit_twitter_rules.py

Audits the live Twitter filtered stream rules against active DB sources.
- Prints all current rules on the API
- Flags any non-"from:username" rules (keyword rules, etc.)
- Flags any "from:username" rules for accounts NOT in the DB
- Flags any DB accounts that are NOT covered by the live rules
- Prints rule count and account coverage summary

Usage:
    python audit_twitter_rules.py
"""

import os
import re
import sys
import httpx

TWITTER_API_BASE = "https://api.twitter.com/2"
RULES_URL = f"{TWITTER_API_BASE}/tweets/search/stream/rules"


def get_token() -> str:
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


def extract_username(url: str) -> str:
    url = url.strip().rstrip("/")
    m = re.search(r"(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    return url.lstrip("@")


def load_db_usernames() -> set[str]:
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_times.settings")
    django.setup()
    from news.models import Source
    usernames: set[str] = set()
    for src in Source.objects.filter(type="twitter", is_active=True):
        raw = (src.url or "").strip()
        if raw.upper() == "ALL":
            continue
        u = extract_username(raw)
        if u:
            usernames.add(u.lower())
    return usernames


def parse_rule_usernames(rule_value: str) -> tuple[set[str], list[str]]:
    """
    Parse a rule string like 'from:foo OR from:bar'.
    Returns (set_of_from_usernames, list_of_non_from_tokens).
    """
    from_users: set[str] = set()
    non_from: list[str] = []
    tokens = [t.strip() for t in re.split(r'\s+OR\s+', rule_value, flags=re.IGNORECASE)]
    for token in tokens:
        m = re.match(r'^from:([A-Za-z0-9_]+)$', token, re.IGNORECASE)
        if m:
            from_users.add(m.group(1).lower())
        elif token:
            non_from.append(token)
    return from_users, non_from


def main():
    token = get_token()
    if not token:
        print("ERROR: TWITTER_BEARER_TOKEN not found.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # ── 1. Fetch live rules ──────────────────────────────────────
    print("Fetching live stream rules from Twitter API...")
    r = httpx.get(RULES_URL, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code}")
        print(r.text[:500])
        sys.exit(1)

    body = r.json()
    rules = body.get("data") or []
    meta = body.get("meta", {})

    print(f"\n{'='*60}")
    print(f"LIVE RULES COUNT: {len(rules)}")
    print(f"{'='*60}")

    if not rules:
        print("No rules found on the API — stream will receive no tweets.")
    else:
        for i, rule in enumerate(rules, 1):
            print(f"\nRule {i}: id={rule['id']}  tag={rule.get('tag','(none)')}")
            print(f"  value: {rule.get('value','')}")

    # ── 2. Load DB usernames ─────────────────────────────────────
    print(f"\n{'='*60}")
    print("Loading active Twitter sources from DB...")
    try:
        db_usernames = load_db_usernames()
    except Exception as e:
        print(f"ERROR loading DB: {e}")
        sys.exit(1)

    print(f"DB active Twitter accounts: {len(db_usernames)}")

    # ── 3. Parse all live rules ──────────────────────────────────
    all_rule_from_users: set[str] = set()
    keyword_rules: list[dict] = []           # rules with non-from tokens
    stale_user_rules: list[tuple] = []       # from:X where X not in DB

    for rule in rules:
        value = rule.get("value", "")
        from_users, non_from = parse_rule_usernames(value)

        if non_from:
            keyword_rules.append({
                "id": rule["id"],
                "tag": rule.get("tag", ""),
                "value": value,
                "bad_tokens": non_from,
            })

        all_rule_from_users.update(from_users)

        # Check each from: user in this rule
        for u in from_users:
            if u not in db_usernames:
                stale_user_rules.append((rule["id"], u, value))

    # DB accounts not covered by any live rule
    missing_from_rules = db_usernames - all_rule_from_users

    # ── 4. Report ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("AUDIT RESULTS")
    print(f"{'='*60}")

    if keyword_rules:
        print(f"\n[FAIL] {len(keyword_rules)} rule(s) contain non-'from:' tokens (keyword/hashtag rules):")
        for kr in keyword_rules:
            print(f"  Rule id={kr['id']} tag={kr['tag']}")
            print(f"    value:      {kr['value']}")
            print(f"    bad tokens: {kr['bad_tokens']}")
    else:
        print("\n[PASS] All rules use only 'from:username' syntax — no keyword rules.")

    if stale_user_rules:
        print(f"\n[FAIL] {len(stale_user_rules)} 'from:' entr(ies) reference accounts NOT in the DB:")
        for rule_id, u, value in stale_user_rules:
            print(f"  @{u}  (rule id={rule_id})")
    else:
        print(f"\n[PASS] All 'from:' accounts in live rules match DB accounts.")

    if missing_from_rules:
        print(f"\n[WARN] {len(missing_from_rules)} DB account(s) NOT covered by any live rule:")
        for u in sorted(missing_from_rules):
            print(f"  @{u}")
    else:
        print(f"\n[PASS] All {len(db_usernames)} DB accounts are covered by live rules.")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Live rules on API:          {len(rules)}")
    print(f"  DB active accounts:         {len(db_usernames)}")
    print(f"  Accounts in live rules:     {len(all_rule_from_users)}")
    print(f"  Keyword/bad rules:          {len(keyword_rules)}")
    print(f"  Stale accounts in rules:    {len(stale_user_rules)}")
    print(f"  DB accounts missing rules:  {len(missing_from_rules)}")

    overall = not keyword_rules and not stale_user_rules and not missing_from_rules
    print(f"\nOverall: {'ALL CLEAN ✓' if overall else 'ISSUES FOUND — see above'}")


if __name__ == "__main__":
    main()
