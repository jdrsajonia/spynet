# SpyNet — Frontend (API Tester)

Frontend **desacoplado** (React + Vite) que consume la API REST de Spynet.
Por ahora es un **probador crudo**: cada pestaña ejecuta un endpoint y muestra
el JSON tal cual lo devuelve el backend. Es la base sobre la que se construirán
las vistas reales (Dashboard, Compare, Historical…).

## Requisitos
- Node.js 18+ y npm
- El backend corriendo en `http://localhost:8000` (`python manage.py runserver`)

## Uso

```bash
cd frontend
npm install
npm run dev        # arranca en http://localhost:5173
```

El puerto `5173` ya está permitido en el CORS del backend.

## Configuración
La URL del backend se define en `.env`:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Pestañas

| Pestaña | Input | Endpoint |
|---|---|---|
| Analyze | URL | `POST /analyses/` |
| Snapshot | URL de Wayback | `POST /analyses/snapshot/` |
| List | — | `GET /analyses/` |
| Detail | id | `GET /analyses/<id>/` |
| Compare | dos URLs | `POST /analyses/compare/` |
| History | dominio | `GET /domains/<name>/analyses/` |
| Stats | — | `GET /stats/` |
