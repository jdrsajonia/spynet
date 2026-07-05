#!/usr/bin/env bash
#
# deploy.sh — actualiza SPYNET en el servidor a la última versión y lo reinicia.
#
# Uso (desde el server, dentro del repo):
#   ./deploy.sh
#
# Requisitos ya montados (setup inicial, una sola vez):
#   - repo clonado en este directorio, con el .venv creado (Python 3.12)
#   - Postgres vía Docker (docker-compose.yml)
#   - servicio systemd 'spynet' (gunicorn) y nginx configurados
#
# Si algo falla, el script corta ahí (set -e) para no dejar un estado a medias.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "==> 1/6  Trayendo el código nuevo (git pull)"
git pull

echo "==> 2/6  Dependencias de Python"
.venv/bin/pip install -q -r requirements.txt

echo "==> 3/6  Asegurando la base de datos (Postgres en Docker)"
docker compose up -d

echo "==> 4/6  Aplicando migraciones de la base de datos"
.venv/bin/python manage.py migrate

echo "==> 5/6  Recompilando el frontend"
cd "$REPO/frontend"
npm ci
npm run build
cd "$REPO"

echo "==> 6/6  Reiniciando el servicio Django (gunicorn)"
sudo systemctl restart spynet

echo ""
echo "==> Listo. Estado del servicio:"
sudo systemctl status spynet --no-pager | head -6
