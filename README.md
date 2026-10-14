# WorldAmaze — Personal Global Intelligence Monitoring Platform

> *"Tell us what matters. We'll watch the world for you."*

WorldAmaze is an editorial-grade, personal global intelligence monitoring platform. Users define topics, geopolitical events, defense aviation milestones, semiconductor export restrictions, or software vulnerabilities in natural language. WorldAmaze parses these requests with **Groq GPT-OSS 120B** into structured, auditable monitoring rules, continuously ingests news from **GNews API** and open **RSS/Atom feeds**, applies deterministic and semantic deduplication, evaluates evidence quality, and delivers immediate alerts or scheduled digests.

---

## 1. Key Capabilities

- **Natural-Language Rule Synthesis**: Converts user prompts into auditable monitoring specifications (subjects, search terms, noise exclusion terms, trigger conditions, evidence requirements, importance thresholds, uncertainty policies, and delivery modes) using Groq GPT-OSS 120B.
- **Multi-Source Ingestion Engine**: Extensible news adapter architecture supporting **GNews API** (with quota exhaustion detection) and independent open **RSS/Atom feeds** (BBC, NPR, Defense News, Defense One, Ars Technica, The Hacker News) as seamless fallbacks.
- **Evidence Verification Policy**: Distinguishes between officially confirmed developments, multiple corroborating sources, single reports, rumors, and speculation. Enforces policies such as suppressing unverified rumors or flagging them for review.
- **Deterministic & Semantic Deduplication**: Normalizes URLs (stripping UTM tracking and query artifacts), generates SHA-256 content hashes, computes token Jaccard similarity, and clusters related stories around stable topic keys to prevent duplicate alert fatigue.
- **Grounded Intelligence Summaries**: Summaries are strictly grounded in retrieved source reporting, citing primary outlets, publication times, and source URLs.
- **Dual Delivery Channels**: In-app notifications with feedback loop (`Relevant`, `Irrelevant`, `Too trivial`, `Duplicate`), plus email delivery via **Resend** for alerts and scheduled digests.
- **Editorial Light-Mode Interface**: Minimal, distraction-free interface built with Jinja2, HTMX, Tailwind CSS, and Lucide icons.

---

## 2. Technology Stack

- **Backend**: Python 3.12+ / 3.13+, FastAPI, Uvicorn, Pydantic v2 & Pydantic Settings, HTTPX, SQLAlchemy 2.x, APScheduler.
- **AI Engine**: Groq API with `openai/gpt-oss-120b` (strict JSON schema outputs and bounded exponential backoff).
- **News Discovery**: GNews API v4 adapter + RSS/Atom feed parser.
- **Database & Auth**: SQLAlchemy 2.x (SQLite for zero-configuration local runs; PostgreSQL/Supabase ready via `DATABASE_URL`), Supabase GoTrue Auth with secure local PBKDF2-HMAC-SHA256 password fallback and signed HTTP-only cookies.
- **Email Delivery**: Resend API (`resend` SDK & HTTPX) with graceful failure handling.
- **Frontend**: Jinja2 server-rendered templates, HTMX for dynamic interactions, Tailwind CSS, Lucide icons, minimal vanilla JavaScript.

---

## 3. Project Structure

```
WorldAmaze/
├── app/
│   ├── main.py                  # FastAPI application entrypoint, lifespan & routes
│   ├── config.py                # Pydantic Settings & safe secret representation
│   ├── database.py              # SQLAlchemy engine, sessionmaker & init_db
│   ├── dependencies.py          # Session authentication & user dependencies
│   ├── models/                  # SQLAlchemy 2.x relational models
│   │   ├── user.py              # User profiles & notification settings
│   │   ├── watch.py             # Watch rules & execution status
│   │   ├── article.py           # Ingested news & RSS articles
│   │   ├── event.py             # Verified intelligence events & links
│   │   ├── match.py             # Audit trail of watch-to-event matches
│   │   ├── notification.py      # In-app and email notification records
│   │   ├── digest.py            # Daily and weekly digest archives
│   │   ├── feedback.py          # User feedback records
│   │   └── run.py               # Monitoring run audit logs
│   ├── schemas/                 # Pydantic v2 validation models
│   ├── services/
│   │   ├── groq_service.py      # Groq GPT-OSS 120B client with retry & backoff
│   │   ├── watch_parser.py      # Prompt-to-rules converter with fallback
│   │   ├── news_service.py      # GNews adapter & ingestion coordinator
│   │   ├── rss_service.py       # Open RSS/Atom feed adapter
│   │   ├── event_matcher.py     # Multi-stage filtering & policy enforcement
│   │   ├── deduplication_service.py # URL canonicalization & content hashing
│   │   ├── summarization_service.py # Source-grounded summary formatter
│   │   ├── notification_service.py  # In-app alerts & Resend email delivery
│   │   ├── digest_service.py    # Digest compilation & email briefings
│   │   └── auth_service.py      # Supabase Auth & PBKDF2 authentication
│   ├── jobs/
│   │   ├── scheduler.py         # APScheduler background runner
│   │   ├── monitoring_job.py    # Active watches surveillance pipeline
│   │   └── digest_job.py        # Periodic digest delivery job
│   ├── templates/               # Jinja2 light-mode templates
│   └── static/                  # CSS styles and JavaScript helpers
├── tests/                       # Automated pytest test suite
├── .env.example                 # Environment configuration template
├── .gitignore                   # Excludes secrets, databases, and caches
├── requirements.txt             # Project dependencies
└── README.md                    # System documentation
```

---

## 4. Local Setup (Windows 11 & PowerShell)

### Step 1: Create and Activate Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Populate `.env` with your API keys:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
GNEWS_API_KEY=your_gnews_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_supabase_anon_publishable_key
RESEND_API_KEY=re_your_resend_api_key_here

# Optional Configurations:
DATABASE_URL=sqlite:///./worldamaze.db
SECRET_KEY=your-secure-random-secret-key
ENVIRONMENT=development
RESEND_FROM_EMAIL=onboarding@resend.dev
DEFAULT_POLLING_INTERVAL_MINUTES=30
```

---

## 5. Running the Application

### Start the FastAPI Server
```powershell
$env:PYTHONPATH="."
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at `http://127.0.0.1:8000`.

- **Public Landing Page**: `http://127.0.0.1:8000/`
- **Register Account**: `http://127.0.0.1:8000/register`
- **Overview Dashboard**: `http://127.0.0.1:8000/dashboard`
- **My Watches**: `http://127.0.0.1:8000/watches`
- **Notifications**: `http://127.0.0.1:8000/notifications`
- **Digests**: `http://127.0.0.1:8000/digests`
- **Event History**: `http://127.0.0.1:8000/history`
- **Settings & Diagnostics**: `http://127.0.0.1:8000/settings`
- **System Health**: `http://127.0.0.1:8000/health`
- **Interactive OpenAPI Docs**: `http://127.0.0.1:8000/docs`

---

## 6. How to Configure External Services

### Supabase PostgreSQL & Auth
1. **Supabase Auth**: The backend automatically calls Supabase GoTrue Auth (`sb.auth.sign_up` and `sb.auth.sign_in_with_password`). If Supabase hosted free-tier rate limits are exceeded (or email confirmation is pending), WorldAmaze seamlessly falls back to secure PBKDF2-HMAC-SHA256 password hashing and signed session cookies.
2. **PostgreSQL Database Connection**: By default, WorldAmaze runs locally with SQLite (`worldamaze.db`) without requiring any PostgreSQL installation. To connect to Supabase PostgreSQL, add the connection string to `.env`:
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```

### Resend Email Gateway
1. Set `RESEND_API_KEY=re_...` in `.env`.
2. For testing without a custom verified domain, Resend requires sender `onboarding@resend.dev` and delivers only to the email address registered with your Resend account.
3. If Resend returns an error (e.g., unverified sender domain), notifications and digests are safely retained in the database, the failure reason is recorded in `email_error`, and in-app alerts remain 100% accessible.

---

## 7. Running Automated Tests

Run the full automated test suite (mocking external API calls to avoid consuming quotas):
```powershell
$env:PYTHONPATH="."
pytest tests/ -v
```

The test suite covers:
- Settings validation and secret masking.
- Watch prompt schema validation and parsing.
- Watch creation, pause, resume, and user ownership isolation.
- URL canonicalization and tracking parameter removal.
- Deterministic content hashing and token Jaccard similarity.
- Event clustering and deduplication keys.
- GNews adapter parsing and quota exhaustion handling.
- RSS adapter ingestion and fallback behavior.
- Event matching with deterministic evidence and importance policies.
- Duplicate notification prevention.
- Digest compilation and generation.
- Session cookie signing and tamper resistance.

---

## 8. Production Deployment & Persistent Workers

In production:
1. **Server Process**: Run Uvicorn behind a reverse proxy (Nginx or Caddy) with Gunicorn or Uvicorn workers:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
2. **Dedicated Background Scheduler**: When running multiple web workers, disable the in-process scheduler (`SCHEDULER_ENABLED=false` in web workers) and run a single standalone scheduler worker to prevent redundant polling jobs:
   ```powershell
   python -c "from app.jobs.scheduler import start_scheduler; import time; start_scheduler(); print('Scheduler worker running...'); time.sleep(99999999)"
   ```
3. Set `ENVIRONMENT=production` in `.env` to enforce HTTPS-only secure cookies and strict security headers.
