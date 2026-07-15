# Database Demonstration Guide

A short, reproducible demonstration of the SpyNet persistence layer.

## 1. Confirm PostgreSQL health

```bash
docker compose up -d db
docker compose ps
```

Expected result: `spynet_postgres_db` reports a healthy status.

## 2. Confirm migrations

```bash
python manage.py showmigrations api
python manage.py migrate
```

Explain that migrations are the versioned history of the database schema.

## 3. Open the ORM shell

```bash
python manage.py shell
```

```python
from api.models import Analysis, Domain, Technology

print(Domain.objects.count())
print(Analysis.objects.count())
print(Technology.objects.count())
```

## 4. Demonstrate relationships

```python
analysis = Analysis.objects.select_related("domain").first()
if analysis:
    print(analysis.domain.name)
    print(list(analysis.technologies.values("name", "category", "confidence")))
    print(list(analysis.errors.values("service", "message")))
```

## 5. Show the generated SQL

```python
query = Analysis.objects.filter(status="partial").select_related("domain")
print(query.query)
```

Explain that the ORM generates SQL; PostgreSQL still performs the query.

## 6. Key points to defend

- `Domain` avoids duplicated domain identities.
- `Analysis` preserves each execution and its source URL.
- `transaction.atomic` prevents incomplete writes after unexpected failures.
- `AnalysisError` preserves expected partial failures.
- `bulk_create` reduces database round trips.
- The Technology XOR constraint is enforced by PostgreSQL.
- Docker volumes preserve data when containers are recreated.

## 7. Close the demonstration

```python
exit()
```

Do not delete or modify records during a presentation unless the demonstration
environment was created specifically for that purpose.

