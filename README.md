# The Crypto Times — Backend

Production-ready Django REST Framework backend for a crypto news verification platform.

## Tech Stack

- **Python 3.11+**
- **Django 4.2** with Django REST Framework
- **SQLite** (swap for PostgreSQL in production)
- **APScheduler** for background news fetching
- **AI Verification** — supports Anthropic Claude, OpenAI GPT-4o, or mock mode

## Project Structure

```
crypto_times_backend/
├── manage.py
├── requirements.txt
├── .env.example
│
├── crypto_times/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── news/                      # Core news app
│   ├── models.py              # Source, NewsArticle, VerificationLog
│   ├── admin.py               # Moderation dashboard
│   ├── apps.py
│   ├── ai/
│   │   └── verifier.py        # AI verification (mock/anthropic/openai)
│   ├── scrapers/
│   │   ├── orchestrator.py    # Central fetch dispatcher
│   │   ├── rss_scraper.py     # RSS/Atom feed scraper
│   │   ├── website_scraper.py # Website content scraper
│   │   ├── twitter_scraper.py # X/Twitter scraper (stub)
│   │   └── images.py          # Auto image fetcher
│   └── management/commands/
│       ├── fetch_news.py      # One-shot fetch command
│       ├── run_scheduler.py   # Background scheduler
│       ├── seed_sources.py    # Seed starter sources
│       └── seed_demo.py       # Seed demo articles
│
├── api/                       # REST API
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── templates/admin/           # Admin template overrides
└── static/                    # Static files
```

## Quick Start

### 1. Set up Python environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
```

Edit `.env` and set your preferences. For development, the defaults work fine (mock AI, no API keys needed).

### 4. Initialize database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Seed data

```bash
# Add starter RSS/website/Twitter sources
python manage.py seed_sources

# OR add demo articles (pre-verified, ready for the frontend)
python manage.py seed_demo
```

### 6. Run the server

```bash
python manage.py runserver
```

The API is now live at **http://127.0.0.1:8000/api/**

Admin panel at **http://127.0.0.1:8000/admin/**

### 7. Start the news scheduler (separate terminal)

```bash
python manage.py run_scheduler
```

This fetches news every 5 minutes (configurable via `FETCH_INTERVAL_MINUTES`).

## API Endpoints

### Public (no auth required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/news/latest` | Paginated approved articles |
| GET | `/api/news/latest?category=DeFi` | Filter by category |
| GET | `/api/news/latest?verdict=REAL` | Filter by AI verdict |
| GET | `/api/news/breaking` | Latest breaking news event |
| GET | `/api/news/{uuid}` | Single article with full detail |
| GET | `/api/sources` | All active monitored sources |
| GET | `/api/sources?type=rss` | Filter sources by type |

### Admin (requires staff auth)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/admin/approve-news` | `{"article_id": "uuid"}` | Approve article |
| POST | `/api/admin/reject-news` | `{"article_id": "uuid"}` | Reject article |
| POST | `/api/admin/edit-news` | `{"article_id": "uuid", "title": "..."}` | Edit article |
| POST | `/api/admin/add-source` | `{"name": "...", "type": "rss", "url": "..."}` | Add source |
| DELETE | `/api/admin/remove-source/{uuid}` | — | Remove source |
| GET | `/api/admin/pending` | — | List pending articles |

### Authentication for Admin Endpoints

Admin endpoints require Django session auth or basic auth. Log in via `/admin/` first, or use:

```bash
curl -u admin:password -X POST http://127.0.0.1:8000/api/admin/approve-news \
  -H "Content-Type: application/json" \
  -d '{"article_id": "uuid-here"}'
```

## AI Verification

Set `AI_PROVIDER` in `.env`:

- **`mock`** (default) — deterministic scores based on content hash, no API key needed
- **`anthropic`** — uses Claude. Set `ANTHROPIC_API_KEY`
- **`openai`** — uses GPT-4o. Set `OPENAI_API_KEY`

## Breaking News Logic

An article is automatically marked as BREAKING when all three conditions are met:

1. AI verdict = `REAL`
2. Confidence score > 90%
3. Admin approves the article

The `/api/news/breaking` endpoint returns the latest breaking article.

## Management Commands

```bash
python manage.py fetch_news        # One-shot fetch from all sources
python manage.py run_scheduler     # Start background scheduler
python manage.py seed_sources      # Add starter sources
python manage.py seed_demo         # Add demo articles for frontend testing
```

## Connecting to the Frontend

Set the frontend's `NEXT_PUBLIC_API_URL` to point to this backend:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

The API response format matches the frontend's TypeScript types exactly.
