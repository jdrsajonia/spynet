# PostgreSQL Quick Reference

Referencia rapida para operar y diagnosticar la base de datos PostgreSQL de SpyNet.

## Start database

```bash
docker compose up -d db
docker compose ps
```

## Django database commands

```bash
python manage.py check
python manage.py showmigrations
python manage.py migrate
python manage.py shell
```

## PostgreSQL console

```bash
docker compose exec db psql -U admin -d spynet-db
```

## Useful SQL

```sql
\dt
\d api_analysis
\d api_technology

SELECT id, source_url, status, analyzed_at
FROM api_analysis
ORDER BY analyzed_at DESC
LIMIT 5;
```

## Troubleshooting

- Confirm Docker Desktop is running.
- Confirm the database container is healthy.
- Use `localhost` when Django runs outside Docker.
- Use `db` when Django runs inside Docker Compose.
- Run migrations before starting the API.
- Check database logs with `docker compose logs db`.

