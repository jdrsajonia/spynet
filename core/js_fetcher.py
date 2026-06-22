import logging
import requests
from urllib.parse import urljoin

from config.settings import DEFAULT_HEADERS, JS_FETCH_TIMEOUT, MAX_JS_FILES, MAX_JS_SIZE

logger = logging.getLogger("spynet.core")

# Patrones en el nombre del archivo que sugieren que vale la pena descargar
PRIORITY_KEYWORDS = [
    "app", "main", "index", "bundle", "vendor",
    "runtime", "chunk", "framework", "core"
]

# Patrones que indican archivos de terceros poco útiles para detección
SKIP_KEYWORDS = [
    "analytics", "gtm", "gtag", "pixel", "tracking",
    "ads", "recaptcha", "stripe", "paypal"
]


def fetch_js_contents(base_url: str, script_srcs: list[str], session=None) -> list[str]:
    """
    Descarga hasta MAX_JS_FILES archivos JS y retorna su contenido como texto.

    Prioriza archivos con nombres que sugieren código de la app (app.js, main.js,
    bundle.js) y omite archivos de terceros o de tracking.

    Args:
        base_url:    URL base del sitio para resolver rutas relativas
        script_srcs: lista de valores src de etiquetas <script>
        session:     requests.Session opcional para reutilizar conexiones.
                     Si es None se usa el módulo requests directamente.

    Returns:
        Lista de strings con el contenido de cada archivo descargado.
        Retorna [] si nada es descargable.
    """
    if not script_srcs:
        return []

    http = session or requests
    candidates = _prioritize(script_srcs)
    logger.debug("JS fetcher: %d candidates after prioritization (from %d srcs)", len(candidates), len(script_srcs))
    contents   = []

    for src in candidates[:MAX_JS_FILES * 2]:  # intentamos más de los que necesitamos por si fallan
        if len(contents) >= MAX_JS_FILES:
            break
        content = _download(src, base_url, http)
        if content:
            logger.debug("Downloaded JS: %s (%d chars)", src[:80], len(content))
            contents.append(content)

    logger.debug("JS fetcher complete: %d/%d files downloaded", len(contents), MAX_JS_FILES)
    return contents


def _prioritize(srcs: list[str]) -> list[str]:
    """
    Ordena los scripts: primero los que tienen keywords de app, luego el resto.
    Descarta los que tienen keywords de terceros.
    """
    priority = []
    rest     = []

    for src in srcs:
        src_lower = src.lower()

        if any(skip in src_lower for skip in SKIP_KEYWORDS):
            continue
        if src_lower.startswith(("http://", "https://")) and not _is_same_origin_hint(src_lower):
            continue  # CDN externo de terceros — poco útil para detectar el stack

        if any(kw in src_lower for kw in PRIORITY_KEYWORDS):
            priority.append(src)
        else:
            rest.append(src)

    return priority + rest


def _is_same_origin_hint(url: str) -> bool:
    """
    Heurística simple: si la URL contiene keywords de frameworks es útil
    aunque sea de un CDN externo (ej: cdn.jsdelivr.net/vue@3/...).
    """
    framework_hints = ["react", "vue", "angular", "next", "nuxt", "jquery",
                       "bootstrap", "tailwind", "webpack", "laravel", "django"]
    return any(h in url for h in framework_hints)


def _download(src: str, base_url: str, http=requests) -> str | None:
    """
    Descarga un archivo JS. Respeta el límite de tamaño y el timeout.
    Retorna None si falla o excede el tamaño máximo.
    """
    try:
        url = urljoin(base_url, src) if not src.startswith("http") else src

        response = http.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=JS_FETCH_TIMEOUT,
            stream=True   # stream para verificar tamaño antes de leer todo
        )

        if response.status_code != 200:
            logger.debug("JS download skipped (HTTP %d): %s", response.status_code, url[:80])
            return None

        content_type = response.headers.get("content-type", "")
        if "javascript" not in content_type and "text" not in content_type:
            logger.debug("JS download skipped (content-type=%s): %s", content_type, url[:80])
            return None

        # Leer con límite de tamaño
        chunks = []
        size   = 0
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="ignore")
            size += len(chunk)
            if size > MAX_JS_SIZE:
                logger.warning("JS file exceeds size limit (%d KB), skipping: %s", MAX_JS_SIZE // 1024, url[:80])
                return None  # archivo demasiado grande, saltarlo
            chunks.append(chunk)

        return "".join(chunks)

    except Exception as exc:
        logger.debug("JS download failed for %s: %s", url[:80], exc)
        return None