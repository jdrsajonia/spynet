# Django ORM Query Examples

Examples for exploring SpyNet data without writing raw SQL.

Start the Django shell:

```bash
python manage.py shell
```

## Imports

```python
from api.models import Analysis, Domain, Technology
```

## Latest analyses

```python
Analysis.objects.select_related("domain").all()[:10]
```

## Analysis history for a domain

```python
Domain.objects.get(name="example.com").analyses.all()
```

## Partial analyses

```python
Analysis.objects.filter(status="partial")
```

## Technologies detected in live analyses

```python
Technology.objects.filter(analysis__isnull=False)
```

## Technologies detected in historical snapshots

```python
Technology.objects.filter(snapshot__isnull=False)
```

## High-confidence server detections

```python
Technology.objects.filter(category="server", confidence__gte=80)
```

## Analyses with their related technologies

```python
analyses = Analysis.objects.select_related("domain").prefetch_related("technologies")
for analysis in analyses:
    print(analysis.domain.name, [tech.name for tech in analysis.technologies.all()])
```

## Count analyses by status

```python
from django.db.models import Count
Analysis.objects.values("status").annotate(total=Count("id")).order_by("status")
```

## Inspect generated SQL

```python
query = Technology.objects.filter(category="server", confidence__gte=80)
print(query.query)
```

These examples are intended for development and demonstrations. Avoid running
large unbounded queries against production data.

