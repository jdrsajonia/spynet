# Welcome to Spynet

![banner](assets/img/spynet_penguins.png)

**Spynet** is a web application that analyzes and maps the technologies used by
websites. It lets you inspect, compare, and understand the technical composition
of web pages — their frontend/backend stack, server, CDN, analytics, DNS, WHOIS,
geolocation, and how all of it has evolved over time via the Wayback Machine.

---

## 🚀 Quick Start

The project has two parts that run together: a **Django backend** (REST API) and a
**React + Vite frontend**. Start the backend first, then the frontend.

### 1. Backend (Django API)

**Prerequisite:** the database runs on **PostgreSQL inside a Docker container**
(see `docker-compose.yml`), so you need **Docker** installed
([Docker Desktop](https://www.docker.com/products/docker-desktop/) on Windows/macOS).

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

# 3. Start the PostgreSQL database (Docker container, runs in the background)
docker compose up -d

# 4. Create the tables inside PostgreSQL
python manage.py migrate

# 5. Run the server
python manage.py runserver
```

The API is now live at **`http://127.0.0.1:8000/`**.

> 🐘 **The database lives in Docker.** `docker compose up -d` starts a PostgreSQL
> container (`spynet_postgres_db`, listening on `localhost:5432`) whose data
> persists in a Docker volume. Django connects to it via the `DATABASES` block in
> `config/settings.py`. **Postgres must be running before `migrate`** — otherwise
> the connection is refused. Useful commands: `docker compose ps` (status),
> `docker compose logs -f` (logs), `docker compose stop` (pause without deleting
> data), `docker compose down` (remove the container; the data volume survives).

> ⚠️ **Don't skip `migrate`.** The database starts **empty** — each clone builds
> its own schema. Without `migrate` the first scan fails with
> `no such table: api_domain`.

### 2. Frontend (React + Vite)

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

---

## 🗂️ Project Structure

```
.
├── manage.py                # Django entry point
├── analyzer.py              # Facade: orchestrates services + detectors for one URL
├── cli.py                   # `spynet` command-line interface
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # PostgreSQL database container
│
├── config/                  # Django project config
│   ├── settings.py          #   DB connection, apps, CORS, throttling
│   ├── urls.py              #   root URL routing
│   └── constants.py         #   scoring constants (timeouts, caps, weights)
│
├── api/                     # REST API (Django app)
│   ├── models.py            #   ORM models = DB tables (Domain, Analysis, Technology…)
│   ├── views.py             #   endpoint logic
│   ├── urls.py              #   /api/v1/... routes
│   ├── persistence.py       #   saves analyzer results into the DB
│   ├── serializers.py       #   request validation
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
│   └── js_fetcher.py        #   downloads JS bundles for deeper detection
│
├── services/                # External-data services (each decoupled)
│   ├── dns_service.py        #   DNS records
│   ├── whois_service.py      #   WHOIS
│   ├── geo_service.py        #   IP geolocation
│   └── wayback_service.py    #   Wayback Machine snapshots
│
├── frontend/                # React + Vite SPA
│   └── src/
│       ├── views/            #   Analyse, Historical, Dashboard, Compare, API Tester
│       ├── components/       #   Sidebar, Topbar, charts…
│       ├── styles/           #   design tokens + per-view CSS
│       └── api.js            #   single layer that talks to the backend
│
└── tests/                   # pytest suite (detectors, services, API)
```

**How the pieces connect:** `analyzer.py` (Facade) runs the `services/` for
infrastructure data and the `detectors/` for technologies, using the patterns in
`core/signatures.json`. `api/views.py` exposes that over HTTP and
`api/persistence.py` stores it through the ORM models into the PostgreSQL database
(running in the Docker container) configured in `config/settings.py`.

---

## 🌐 REST API

Base URL: `http://127.0.0.1:8000/api/v1/`

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

> `POST /analyses/` runs a full live analysis and **persists** it, so it is then
> retrievable via `GET /analyses/<id>/`, comparable via `/analyses/compare/`, and
> aggregated in `/stats/`. `POST /analyses/historical/` is heavier: it downloads
> and analyzes ~12 archived captures. The `ai-analyses/` endpoint is still a stub.

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

---

## ⚙️ What does it analyze?

Given a domain, Spynet retrieves:

- 🧩 Technologies — frontend, backend, server, CDN, analytics (with version when detectable)
- 🌐 Domain information (WHOIS)
- 📡 DNS records (all IPs, nameservers, MX)
- 📍 IP geolocation
- 📅 Historical snapshots and the technology stack of each (Wayback Machine)

The frontend exposes this through several views: **Analyse**, **Historical**,
**Dashboard**, **Compare**, and a raw **API Tester**.

---

## 🛠️ Stack

- Python / Django + Django REST Framework
- PostgreSQL (runs in a Docker container via `docker-compose.yml`)
- React + Vite (frontend)
- pytest (tests)
- GitHub Actions (Continuous Integration)
---

## ✅ Tests

```bash
pytest
```
Continuous Integration:
This project uses GitHub Actions for Continuous Integration (CI).
On every push and pull request, GitHub automatically:

- Sets up a Python 3.12 environment.
- Starts a PostgreSQL service.
- Installs project dependencies.
- Applies Django database migrations.
- Runs the complete test suite using pytest.
This workflow helps detect issues early and ensures that every change is automatically validated before being merged into the main branch.
---

## 📌 Status

Project under development for **Software Engineering II**.

Preview available at: https://jdrsajonia.github.io

---

<p align="center">
  <img src="assets/img/tux_spynet_profesional.png" width="120"/>
</p>

<p align="center">
  <i>Watching every system. Auditing every weakness.</i>
</p>
