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
