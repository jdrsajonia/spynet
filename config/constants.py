DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {"User-Agent": DEFAULT_USER_AGENT}

# HTTP timeouts (seconds)
REQUEST_TIMEOUT = 10    # main page fetch
PROBE_TIMEOUT   = 5     # path probing (strategy 3)
JS_FETCH_TIMEOUT = 6    # JS file download
WAYBACK_TIMEOUT  = 15   # Wayback CDX API

# JS fetcher limits
MAX_JS_FILES = 3
MAX_JS_SIZE  = 500_000  # bytes — skip bundles larger than 500 KB

# Score assigned to a confirmed probe-path hit (strategy 3)
PROBE_PATH_SCORE = 60

# Confidence dada a una tecnología inferida por `implies` (no observada
# directamente, sino deducida de otra que sí se detectó). Deliberadamente baja:
# es una pista razonable del stack, no una detección con evidencia propia.
IMPLIED_CONFIDENCE = 40

# Concurrencia del sondeo de rutas (estrategia 3). Las rutas se piden en
# paralelo para que todas quepan dentro del presupuesto de tiempo.
PROBE_MAX_WORKERS = 6

# Robustez del scoring: máximo de coincidencias que aportan score por categoría.
# Evita que una tecnología con muchos patrones débiles acumule score sin límite
# y cruce el threshold con evidencia ruidosa. Una tech legítima cruza su umbral
# con 1-2 matches en su categoría dominante; más allá de eso no aporta confianza real.
MAX_CATEGORY_MATCHES = 2
