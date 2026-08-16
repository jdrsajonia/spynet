# Welcome to Spynet

![banner](assets/img/spynet_penguins.png)

**Spynet** is a web application that analyzes and maps the technologies used by
websites. It lets you inspect, compare, and understand the technical composition
of web pages — their frontend/backend stack, server, CDN, analytics, DNS, WHOIS,
geolocation, and how all of it has evolved over time via the Wayback Machine.

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🛠️ Tech Stack](#-tech-stack)
- [🚀 Getting Started](#-getting-started)
  - [Option A — Full stack with Docker Compose](#option-a--full-stack-with-docker-compose)
  - [Option B — Manual setup (mirrors production)](#option-b--manual-setup-mirrors-production)
  - [AI Assistant (Gemini)](#ai-assistant-gemini)
- [🗂️ Project Structure](#-project-structure)
- [🌐 REST API](#-rest-api)
- [💻 CLI](#-cli)
- [🧬 How detection works (scoring model)](#-how-detection-works-scoring-model)
- [✅ Tests](#-tests)
- [📌 Status](#-status)

---

## ✨ Features

Given a domain, Spynet retrieves:

- 🧩 **Technologies** — frontend, backend, server, CDN, analytics (with version when detectable)
- 🌐 **Domain information** (WHOIS)
- 📡 **DNS records** (all IPs, nameservers, MX)
- 📍 **IP geolocation**
- 🔒 **Passive security posture** — a graded (A–F) audit from the captured data
- 📅 **Historical snapshots** and the technology stack of each (Wayback Machine)
- 🤖 **AI assistant** — ask questions about a scanned site (Google Gemini, with a local fallback)

The frontend exposes all of this through several views: **Home**, **Analyse**,
**Historical**, **Dashboard**, **Compare**, and **API Docs**.

---

## 🛠️ Tech Stack

- **Backend:** Python / Django + Django REST Framework
- **Database:** PostgreSQL (runs in a Docker container via `docker-compose.yml`)
- **Frontend:** React + Vite
- **Tests:** pytest
- **CI:** GitHub Actions (runs the suite on every push and pull request)

> **Deployment note.** The public site runs a **hybrid** setup: Django via
> gunicorn/systemd, the frontend served by nginx, and PostgreSQL in Docker. The
> fully-containerized flow below (Option A) is meant for **local development**.

---

## 🚀 Getting Started

The project has two parts that run together: a **Django backend** (REST API) and a
**React + Vite frontend**. You can bring everything up with a single Docker Compose
command (**Option A**), or run each part by hand (**Option B**).

**Prerequisite for both:** [Docker](https://www.docker.com/products/docker-desktop/)
— the database always runs in a container.

### Option A — Full stack with Docker Compose

The quickest way to get a working environment: one command builds and starts the
database, the backend, and the frontend together.

```bash
# 1. Create your .env (the backend container reads it — the file must exist
#    even if you don't set a Gemini key yet)
cp .env.example .env          # Linux / macOS
# copy .env.example .env      # Windows (PowerShell)

# 2. Build and start everything (db + backend + frontend), in the background
docker compose up -d
```

That's it. Docker starts three services:

| Service | Container | URL |
|---------|-----------|-----|
| Frontend (Vite) | `spynet_frontend` | http://localhost:5173 |
| Backend (Django) | `spynet_backend` | http://localhost:8000/api/v1/ |
| Database (Postgres) | `spynet_postgres_db` | `localhost:5432` |

The backend container **runs migrations automatically** on start, so the schema is
ready without extra steps. Useful commands: `docker compose ps` (status),
`docker compose logs -f` (live logs), `docker compose down` (stop and remove the
containers; the database volume survives).

> ℹ️ This mode is for **local development** only. For the production layout see the
> deployment note above.

### Option B — Manual setup (mirrors production)

Run each part yourself, with only PostgreSQL in Docker. This mirrors how the
project runs in production (Python process + separate frontend + Postgres
container), which makes it the better choice when you're debugging deployment.

#### 1. Backend (Django API)

From the project root:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    Linux / macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start ONLY the PostgreSQL database (Docker container, in the background)
docker compose up -d db

# 4. Create the tables inside PostgreSQL
python manage.py migrate

# 5. Run the server
python manage.py runserver
```

The API is now live at **`http://127.0.0.1:8000/`**.

> 🐘 **The database lives in Docker.** `docker compose up -d db` starts a PostgreSQL
> container (`spynet_postgres_db`, listening on `localhost:5432`) whose data
> persists in a Docker volume. Naming the `db` service explicitly is deliberate:
> a bare `docker compose up -d` would also start the `backend` and `frontend`
> containers (that's Option A). Django connects via the `DATABASES` block in
> `config/settings.py`. **Postgres must be running before `migrate`** — otherwise
> the connection is refused. Useful: `docker compose ps` (status),
> `docker compose logs -f db` (logs), `docker compose stop db` (pause without
> deleting data), `docker compose down` (remove the container; the data volume
> survives).

> ⚠️ **Don't skip `migrate`.** The database starts **empty** — each clone builds
> its own schema. Without `migrate` the first scan fails with
> `no such table: api_domain`.

#### 2. Frontend (React + Vite)

In a **second terminal**, with the backend still running:

```bash
cd frontend
npm install        # first time only
npm run dev        # dev server at http://localhost:5173
```

Open **`http://localhost:5173`**. Port `5173` is already allowed in the backend's
CORS config, so keep **both** servers running: Django on `:8000`, Vite on `:5173`.

The backend URL is configured in `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

> **Tip:** live analysis hits external services (DNS, WHOIS, Geo, Wayback), so
> heavy domains like `google.com` can take a while. Use `example.com` for quick
> tests.

### AI Assistant (Gemini)

The **Analyse** view includes an AI chat assistant that answers questions about
the scanned site. It uses Google Gemini when a key is configured, and falls back
to a local rule-based engine otherwise — so it works either way.

```bash
# 1. Copy the example file (only once)
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS

# 2. Edit .env and paste your own Gemini API key
#    GEMINI_API_KEY=AIza...your-key...
#    GEMINI_MODEL=gemini-2.5-flash
```

Django reads `.env` automatically on startup — no need to export variables
manually. Restart the backend if it was already running.

> ⚠️ **`.env` is git-ignored.** Never commit it. Each team member creates their
> own `.env` with their own key. If the key is missing or invalid, the assistant
> still works using the local fallback (`provider: "local"`).

> 🔒 **The API key lives only in the backend.** It is never sent to the browser.
> Do **not** add `GEMINI_API_KEY` to `frontend/.env` — that file is for public
> variables like `VITE_API_BASE_URL` only.

---

## 🗂️ Project Structure

<details>
<summary>Full directory tree</summary>

```
.
├── manage.py                # Django entry point
├── analyzer.py              # Facade: orchestrates services + detectors for one URL
├── cli.py                   # `spynet` command-line interface
├── requirements.txt         # Python dependencies (runtime)
├── requirements-dev.txt     # dev/test dependencies (pytest, linters)
├── pyproject.toml           # tooling config (ruff, pytest, etc.)
├── docker-compose.yml       # PostgreSQL database + (dev) backend/frontend containers
├── Dockerfile.backend       # backend image (Option A)
├── .env.example             # sample environment variables
│
├── config/                  # Django project config
│   ├── settings.py          #   DB connection, apps, CORS, throttling
│   ├── urls.py              #   root URL routing
│   ├── constants.py         #   scoring constants (timeouts, caps, weights)
│   ├── env_loader.py        #   loads/validates environment variables
│   ├── logging_config.py    #   logging setup
│   ├── asgi.py / wsgi.py    #   ASGI/WSGI entrypoints
│
├── api/                     # REST API (Django app)
│   ├── models.py            #   ORM models = DB tables (Domain, Analysis, Technology…)
│   ├── views.py             #   endpoint logic
│   ├── urls.py              #   /api/v1/... routes
│   ├── admin.py             #   Django admin registration
│   ├── persistence.py       #   saves analyzer results into the DB
│   ├── ai_assistant.py      #   AI chat assistant for the Analyse panel (Gemini + fallback)
│   ├── apps.py              #   Django app config
│   ├── serializers/         #   request/response validation (analysis, compare, snapshot)
│   ├── utils/               #   response envelope, error codes, exception handler
│   └── migrations/          #   DB schema history (applied by `migrate`)
│
├── detectors/               # Technology detection (Strategy pattern)
│   ├── base_detector.py     #   shared scoring/matching logic
│   ├── frontend_detector.py #   one detector per category…
│   ├── backend_detector.py
│   ├── cdn_detector.py
│   ├── server_detector.py
│   ├── analytics_detector.py
│   └── detector_factory.py  #   builds detectors from signatures (Factory)
│
├── core/
│   ├── signatures.json      # the pattern database (all technologies + weights)
│   ├── signature_loader.py  #   loads signatures once (Singleton)
│   ├── js_fetcher.py        #   downloads JS bundles for deeper detection
│   └── security_auditor.py  #   passive security posture grade (A–F) from captured data
│
├── services/                # External-data services (each decoupled)
│   ├── base_services.py      #   abstract base (fetch_service contract)
│   ├── dns_service.py        #   DNS records
│   ├── whois_service.py      #   WHOIS
│   ├── geo_service.py        #   IP geolocation
│   ├── tls_service.py        #   TLS/certificate inspection
│   └── wayback_service.py    #   Wayback Machine snapshots
│
├── frontend/                # React + Vite SPA
│   ├── Dockerfile.front      #   frontend image (Option A)
│   └── src/
│       ├── views/            #   Home, Analyse, Historical, Dashboard, Compare, API Docs
│       ├── components/       #   Sidebar, Topbar, AiChatPanel, MapEmbed, charts/…
│       ├── styles/           #   design tokens + per-view CSS
│       ├── utils/            #   categories + formatting helpers
│       └── api.js            #   single layer that talks to the backend
│
├── tests/                   # pytest suite (api, detectors, services, AI, security)
│
├── docs/                    # workshops, UML class diagram
└── assets/                  # logos & architecture diagram
```

</details>

**How the pieces connect:** `analyzer.py` (Facade) runs the `services/` for
infrastructure data and the `detectors/` for technologies, using the patterns in
`core/signatures.json`. `api/views.py` exposes that over HTTP and
`api/persistence.py` stores it through the ORM models into the PostgreSQL database
(running in the Docker container) configured in `config/settings.py`.

---

## 🌐 REST API

Base URL: `http://127.0.0.1:8000/api/v1/`

The API describes itself. The **API Docs** view in the frontend reads the OpenAPI
document and renders it in SpyNet's own design, with a *Try it* form per endpoint —
that is the one to use day to day. The backend also serves the standard renderings:

| URL | What it is |
|-----|-----------|
| [`/api/v1/docs/`](http://127.0.0.1:8000/api/v1/docs/) | **Swagger UI** — every endpoint, its parameters, its response schema, and a *Try it out* button |
| [`/api/v1/redoc/`](http://127.0.0.1:8000/api/v1/redoc/) | Redoc — the same thing, laid out for reading |
| [`/api/v1/schema/`](http://127.0.0.1:8000/api/v1/schema/) | The raw OpenAPI 3 document, to generate clients from |

It is generated from the views and serializers by
[drf-spectacular](https://drf-spectacular.readthedocs.io/), so it cannot drift from
the code. Add an endpoint and it shows up; change a field and the schema changes.

<details>
<summary>Full API reference — envelope, error codes, rate limits, endpoints, examples</summary>

Regenerate the OpenAPI document to a file with:

```bash
python manage.py spectacular --file schema.yaml
```

### Authentication

There is none. The API is public and every endpoint is anonymous.

### Response envelope

**Every** response — success or failure — has the same four keys. The payload
documented for each endpoint is what you find under `data`:

```json
{ "success": true, "data": { "id": 1, "domain": "github.com" }, "error": null, "meta": { "analysis_id": 1 } }
```

On failure `data` is `null` and `error` carries the code and a human-readable message:

```json
{ "success": false, "data": null, "error": { "code": "VALIDATION_ERROR", "message": "Enter a valid URL." }, "meta": { "fields": { "url": ["Enter a valid URL."] } } }
```

`meta` is endpoint-specific: page counters on the list endpoint, `analysis_id` on the
ones that persist an analysis, `fields` on validation errors.

### Error codes

| `error.code` | HTTP | When |
|--------------|------|------|
| `VALIDATION_ERROR` | 400 | The body or query string failed validation. `meta.fields` details each field. |
| `MISSING_QUESTION` | 400 | `POST /ai-analyses/` without a `question`. |
| `MISSING_ANALYSIS` | 400 | `POST /ai-analyses/` without an `analysis` object. |
| `NOT_FOUND` | 404 | No such analysis, domain, or Wayback capture. |
| `METHOD_NOT_ALLOWED` | 405 | The endpoint does not accept that HTTP method. |
| `RATE_LIMITED` | 429 | You exceeded a rate limit (see below). Back off and retry. |
| `EXTERNAL_SERVICE_ERROR` | 502 | An upstream service (Wayback, `ip-api.com`, WHOIS…) failed or timed out. |
| `INTERNAL_ERROR` | 500 | Unexpected server-side failure. |

### Rate limits

Per IP address. Exceeding any of them returns `429 RATE_LIMITED`.

| Scope | Limit | Applies to |
|-------|-------|-----------|
| general | 60/min | every endpoint |
| `analyze` | 10/min | the endpoints that run a live analysis: `POST /analyses/`, `/analyses/snapshot/`, `/analyses/historical/`, `/analyses/<id>/wayback/`, `POST /analyses/compare/` |
| `ai` | 15/min | `POST /ai-analyses/` |

### Pagination

`GET /analyses/` takes `?page=` (1-based, default `1`) and `?page_size=` (default `20`,
capped at `100`). The counters come back in `meta`:

```json
{ "meta": { "page": 2, "pages": 7, "total": 134, "page_size": 20 } }
```

### CORS

The browser can only call the API from an allowed origin. Defaults to the Vite and CRA
dev servers (`:5173`, `:3000` on both `localhost` and `127.0.0.1`); override with the
`DJANGO_CORS_ORIGINS` environment variable (comma-separated).

### Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/analyses/` | Analyze a URL (live) and persist the result |
| `GET`  | `/analyses/` | List saved analyses (paginated) |
| `GET`  | `/analyses/<id>/` | Get a saved analysis |
| `POST` | `/analyses/<id>/wayback/` | Load Wayback snapshots for an analysis |
| `POST` | `/analyses/snapshot/` | Analyze a single Wayback snapshot (passive) |
| `POST` | `/analyses/historical/` | Analyze technologies across all snapshots of a domain |
| `POST` | `/analyses/compare/` | Compare two URLs (A/B) |
| `GET`  | `/analyses/compare/?a=1&b=2` | Compare two saved analyses by id |
| `GET`  | `/domains/<name>/analyses/` | All analyses for a domain |
| `GET`  | `/stats/` | Aggregated stats across stored analyses |
| `POST` | `/ai-analyses/` | Ask the AI assistant about an analysis |

> `POST /analyses/` runs a full live analysis and **persists** it, so it is then
> retrievable via `GET /analyses/<id>/`, comparable via `/analyses/compare/`, and
> aggregated in `/stats/`. `POST /analyses/historical/` is heavier: it downloads
> and analyzes ~12 archived captures.

### Example requests

**PowerShell (Windows):**
```powershell
# Analyze a URL
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/api/v1/analyses/ -ContentType "application/json" -Body '{"url": "example.com"}' | ConvertTo-Json -Depth 10

# Get an analysis
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/analyses/1/ | ConvertTo-Json -Depth 10
```

**curl (Linux/macOS):**
```bash
# Analyze a URL
curl -X POST http://127.0.0.1:8000/api/v1/analyses/ -H "Content-Type: application/json" -d '{"url": "example.com"}'

# Get an analysis
curl http://127.0.0.1:8000/api/v1/analyses/1/
```

**VSCode REST Client** — create a `test.http` file:
```http
POST http://127.0.0.1:8000/api/v1/analyses/
Content-Type: application/json

{"url": "example.com"}

###

GET http://127.0.0.1:8000/api/v1/analyses/1/
```

</details>

---

## 💻 CLI

Spynet also ships a command-line interface. Install the package in editable mode
from the project root (registers the `spynet` command pointing at the local
source, so code changes take effect immediately):

```bash
pip install -e .
```

```bash
# Basic analysis
spynet example.com

# Full WHOIS and geo data
spynet example.com --depth

# Analyze a Wayback Machine snapshot
spynet example.com --snapshot <wayback-url>
```

Output is JSON printed to stdout.

---

## 🧬 How detection works (scoring model)

Technology detection is the core of Spynet. Every technology is described in
[`core/signatures.json`](core/signatures.json) by a set of **patterns** grouped
into categories (HTML, script `src`, headers, cookies, downloaded JS, static
resources, DNS/IP for CDNs). A `DetectorFactory` builds one detector per category
(`frontend`, `backend`, `cdn`, `server`, `analytics`) following the **Strategy**
pattern.

<details>
<summary>Weighted scoring and robustness rules</summary>

### Weighted scoring

Each category has a `weight`. For every matching pattern the detector adds that
weight to a running `score`, then compares the total against the technology's
`threshold`. If `score >= threshold`, the technology is reported with a
`confidence` (capped at 100) and the list of evidence that triggered it.

```
score = Σ (weight_category × matches_in_category)   →   detected if score >= threshold
```

Signals across categories accumulate, so a strong header **plus** a matching
cookie reinforce each other, while a single weak signal is usually not enough.

### Robustness: two design rules

Adding more signatures does **not** make detection more robust by itself — the
opposite, in fact. Two rules keep it accurate:

1. **Per-category cap** (`MAX_CATEGORY_MATCHES` in `config/constants.py`).
   At most *N* matches per category contribute to the score (the evidence still
   lists them all). This stops a technology with many weak patterns from
   accumulating an inflated score and crossing its threshold on noise alone.

2. **Pattern specificity.** A pattern only earns a high weight if it is
   *discriminant* — i.e. it does not appear across many unrelated frameworks.
   Generic signals (e.g. `x-content-type-options`, `x-requested-with`) are
   removed or given a low weight. Substring traps are avoided too: for example
   `@remix-run/` was dropped because it is shipped by **React Router**, not only
   by the Remix framework, and short `ng*` tokens were removed because they
   match unrelated minified identifiers (`ngComponent` ⊂ `renderingComponent`).

> **Takeaway:** robustness comes from the *cap* and *specificity*, not from the
> number of signatures. Every false positive we found during validation was a
> non-discriminant pattern, never a missing one.

</details>

---

## ✅ Tests

Run the test suite locally:

```bash
pytest
```

To measure test coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

Continuous Integration is configured with GitHub Actions, which automatically runs
the test suite on every push and pull request.

---

## 📌 Status

Project under development for *Software Engineering II*.

Presentation available at: https://jdrsajonia.github.io

Public site at: http://149.130.185.58

---

<p align="center">
  <img src="assets/img/tux_spynet_profesional.png" width="120"/>
</p>

<p align="center">
  <i>Watching every system. Auditing every weakness.</i>
</p>
