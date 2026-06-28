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
| `GET` | `/api/v1/analyses/compare/?ids=1,2` | Compare two analyses |
| `GET` | `/api/v1/stats/` | General stats |

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

> **Note:** Views are currently stubs — all endpoints return `{"message": "not implemented"}`. The routing, validation, and error handling are fully functional.

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
