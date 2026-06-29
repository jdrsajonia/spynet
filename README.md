# Welcome to Spynet

![banner](assets/img/spynet_penguins.png)

**Spynet** is a web application designed to analyze and map the technologies used by websites. It allows users to inspect, compare, and understand the technical composition of different web pages in a structured way.

---

## 🚀 Project Develop

Spynet goes beyond simple technology detection. The system:

- 📊 Analyzes the technological structure of a website  
- 🗄️ Stores results in a database  
- 🔍 Allows comparison between multiple websites  
- 🔌 Exposes data through a REST API  

This turns it into a small **web intelligence repository**, useful for both analysis and learning.

---

## ⚙️ What does it analyze?

Given a domain, Spynet can retrieve:

- 🧩 Technologies (frontend, backend, services)  
- 🌐 Domain information (WHOIS)  
- 📡 DNS data  
- 📅 Historical snapshots (optional)  

---

## 🔍 Main Features

- URL analysis  
- Results visualization  
- Website comparison  
- API access  
- Analysis storage  

---

## 🧠 Approach

The system follows a modular architecture:

- Backend built with Django + REST API  
- Decoupled services for each type of analysis  
- Relational database for persistence  
- Scalable towards historical and analytical features  

---

## 🧬 How detection works (scoring model)

Technology detection is the core of Spynet. Every technology is described in
[`core/signatures.json`](core/signatures.json) by a set of **patterns** grouped
into categories (HTML, script `src`, headers, cookies, downloaded JS, static
resources, DNS/IP for CDNs). A `DetectorFactory` builds one detector per category
(`frontend`, `backend`, `cdn`, `server`) following the **Strategy** pattern.

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

## 🛠️ Stack

- Python / Django  
- Django REST Framework  
- SQLite / PostgreSQL  
- Docker  
- GitHub Actions  

---

## 💻 CLI — Quick Start

### Installation

Clone the repo and install in editable mode from the project root:

```bash
pip install -e .
```

This registers the `spynet` command in your PATH, pointing directly to the local source so any code change takes effect immediately without reinstalling.

### Usage

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

## 🌐 REST API — Local Development

### Start the server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/api/v1/analyses/` | Analyze a URL |
| `POST` | `/api/v1/analyses/snapshot/` | Analyze a Wayback Machine snapshot |
| `GET` | `/api/v1/analyses/<id>/` | Get a saved analysis |
| `GET` | `/api/v1/analyses/compare/?a=1&b=2` | Compare two saved analyses |
| `GET` | `/api/v1/stats/` | Aggregated stats across stored analyses |

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

> **Note:** `POST /analyses/` runs a full live analysis and **persists** it; the
> result is then retrievable via `GET /analyses/<id>/`, comparable via
> `/analyses/compare/`, and aggregated in `/stats/`. `POST /analyses/snapshot/`
> runs a passive analysis over a Wayback snapshot (not persisted). The
> `ai-analyses/` endpoint is still a stub.

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
