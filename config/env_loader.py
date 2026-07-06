"""
Loader simple de archivos ``.env`` usando solo la standard library.

Lee pares ``KEY=VALUE`` del archivo ``.env`` en la raíz del proyecto y los
inyecta en ``os.environ`` **sin sobrescribir** variables que ya existan (las
variables de entorno explícitas del sistema siempre tienen prioridad).

Se ejecuta una sola vez al importar ``config.settings``, antes de que
cualquier otro módulo lea variables con ``os.environ.get()``.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_dotenv(base_dir: Path) -> None:
    """Carga el archivo ``.env`` desde *base_dir* (raíz del proyecto)."""
    env_path = base_dir / ".env"
    if not env_path.is_file():
        logger.debug("env_loader: %s no encontrado, saltando.", env_path)
        return

    loaded = 0
    skipped = 0

    with open(env_path, encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()

            # Ignorar vacías y comentarios
            if not line or line.startswith("#"):
                continue

            # Debe tener al menos un '='
            if "=" not in line:
                logger.debug("env_loader: línea %d ignorada (sin '='): %s", lineno, line[:40])
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Validar que el key sea un identificador válido
            if not key or not key.replace("_", "").isalnum():
                logger.debug("env_loader: línea %d ignorada (key inválido): %s", lineno, key[:30])
                continue

            # Remover comillas envolventes (simples o dobles)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            # No sobrescribir variables ya existentes en el entorno
            if key in os.environ:
                skipped += 1
                continue

            os.environ[key] = value
            loaded += 1

    if loaded or skipped:
        logger.info(
            "env_loader: cargado .env — %d variable(s) inyectadas, %d ya existentes (no sobrescritas).",
            loaded,
            skipped,
        )
