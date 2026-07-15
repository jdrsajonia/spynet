# Database Migration Runbook

Safe procedure for applying Django model changes to the SpyNet PostgreSQL schema.

## Before changing a model

```bash
git status
git pull --rebase origin main
docker compose up -d db
python manage.py showmigrations
```

## Generate a migration

After editing `api/models.py`:

```bash
python manage.py makemigrations api
```

Review the generated file under `api/migrations/`. Confirm that it contains only
the intended operations.

## Apply and validate

```bash
python manage.py migrate
python manage.py check
python manage.py showmigrations api
pytest -q
```

## Verify that no migration is missing

```bash
python manage.py makemigrations --check --dry-run
```

The command should report `No changes detected`.

## Inspect generated SQL

```bash
python manage.py sqlmigrate api MIGRATION_NUMBER
```

Replace `MIGRATION_NUMBER` with a value such as `0006`.

## Commit scope

Commit the model change, its migration and its tests together:

```bash
git add api/models.py api/migrations tests
git commit -m "db: describe the schema change"
```

## Recovery rules

- Do not delete an applied migration from a shared branch.
- Do not edit migration history already used by teammates.
- Create a corrective migration instead.
- Back up important data before destructive schema operations.
- Check `docker compose logs db` when PostgreSQL is unavailable.

