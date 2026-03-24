# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server
python manage.py runserver

# Background news scheduler (separate terminal)
python manage.py run_scheduler

# One-shot news fetch
python manage.py fetch_news

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Seed data
python manage.py seed_sources   # Add starter RSS/website/Twitter sources
python manage.py seed_demo      # Add pre-verified demo articles

# Production build (Railway/Render)
bash build.sh
```

No test suite is currently configured.

## Architecture

Django REST Framework backend with two apps:

- **`news/`** — models, admin panel, scrapers, AI verification, background scheduler
- **`api/`** — REST API views and serializers (thin layer over `news/`)

### Data Flow

The background scheduler (`news/scheduler.py`) runs every `FETCH_INTERVAL_MINUTES` (default: 5) via APScheduler, which starts automatically on Django boot. It calls the orchestrator (`news/scrapers/orchestrator.py`), which dispatches to each active `Source` by type (rss, website, twitter, whale_monitor). The orchestrator rate-limits AI verification to 10 articles per cycle with a 7-second delay between calls (Groq free tier).

Scraped articles become `NewsArticle` objects with `status=pending`. AI verification (`news/ai/verifier.py`) sets `ai_verdict` (REAL/FAKE/UNCERTAIN), `confidence_score`, `explanation`, `description`, and `key_points`. An article becomes breaking news only when: `ai_verdict=REAL` + `confidence_score > 90` + admin approves it.

### Models

Three models in `news/models.py`:
- **`Source`** — news sources with type (rss/twitter/website/whale_monitor), ManyToMany `owners` (admin users see only their own sources)
- **`NewsArticle`** — articles with AI verification fields, JSON `images` and `tags`, `status` (pending/approved/rejected), `is_breaking` flag
- **`VerificationLog`** — per-article AI verification history with raw provider responses

### AI Verification

Configured via `AI_PROVIDER` env var. Supported: `groq` (default, Llama 3.3-70b), `anthropic`, `openai`, `alibaba`, `mock` (development, no API key needed). The verifier returns verdict, confidence (0-100), explanation, a journalist-style description, and 3 key_points bullet points.

### Whale Monitor

`news/scrapers/whale_scraper.py` monitors on-chain transactions using Mempool.space (BTC), Etherscan (ETH), and CoinGecko (prices). Minimum thresholds: 500 BTC / 5000 ETH / $10M stablecoins. Has a 30+ wallet address database mapping known exchanges/treasuries. High-confidence whale alerts auto-set `ai_verdict` without calling the AI verifier.

### API

All endpoints under `/api/`. Public: `/api/news/latest`, `/api/news/breaking`, `/api/news/{uuid}`, `/api/sources`. Admin (staff auth required): `/api/admin/pending`, `/api/admin/approve-news`, `/api/admin/reject-news`, `/api/admin/edit-news`, `/api/admin/add-source`, `/api/admin/remove-source/{uuid}`, `/api/admin/recent-articles`. REST framework is configured with camelCase JSON responses (djangorestframework-camel-case).

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | AI backend (`groq`, `anthropic`, `openai`, `alibaba`, `mock`) |
| `GROQ_API_KEY` | Groq API key |
| `FETCH_INTERVAL_MINUTES` | Scheduler interval (default: 5) |
| `ETHERSCAN_API_KEY` | Etherscan for ETH whale monitoring |
| `TWITTER_BEARER_TOKEN` | Twitter/X API v2 |
| `DATABASE_URL` | PostgreSQL connection (defaults to localhost:5432/cryptotimes) |
| `DEBUG` | Django debug mode |
