import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables desde .env (raíz del proyecto) antes de leer os.environ.
# No sobrescribe variables ya definidas en el entorno del sistema.
from config.env_loader import load_dotenv  # noqa: E402
load_dotenv(BASE_DIR)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-me-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Orígenes permitidos para el frontend (Vite :5173, CRA/Next :3000 por defecto en dev).
CORS_ALLOWED_ORIGINS = os.environ.get(
    "DJANGO_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
).split(",")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    },
]

STATIC_URL = "static/"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'spynet-db',
        'USER': 'admin',
        'PASSWORD': 'admin123',
        'HOST': 'localhost',        
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "api.utils.exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Límite general por IP para no abusar de la API.
        "anon": "60/min",
        # Límite estricto para los endpoints que disparan análisis en vivo:
        # protege los servicios externos, sobre todo ip-api.com (45 req/min).
        "analyze": "10/min",
        # Chat de IA: protege la cuota (y el costo) de la API de Gemini.
        "ai": "15/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SpyNet API",
    "DESCRIPTION": (
        "Detects the technology stack of a website, live or from Wayback Machine "
        "snapshots, and stores the results for comparison and aggregate stats.\n\n"
        "**Every response is wrapped in an envelope** — the payload documented for "
        "each endpoint is what you find under `data`:\n\n"
        "```json\n"
        '{"success": true, "data": {...}, "error": null, "meta": {}}\n'
        "```\n\n"
        "On failure, `data` is `null` and `error` holds `{code, message}`. See the "
        "`ErrorResponse` schema for the list of `code` values.\n\n"
        "The API is public: no authentication is required. It is rate limited per IP "
        "(60/min overall, 10/min for the endpoints that run a live analysis, "
        "15/min for the AI assistant). Exceeding a limit returns `429 RATE_LIMITED`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,  # no documentar el endpoint del propio esquema
    "SCHEMA_PATH_PREFIX": "/api/v1",
    # Sin esto, cada enum arrastra una descripción que repite sus propios valores
    # ("* `completed` - completed…"). El tipo del campo ya los muestra.
    "ENUM_GENERATE_CHOICE_DESCRIPTION": False,
    "TAGS": [
        {"name": "analyses", "description": "Run and retrieve technology analyses."},
        {"name": "domains", "description": "History of analyses per domain."},
        {"name": "stats", "description": "Aggregate metrics across stored analyses."},
        {"name": "ai", "description": "AI assistant over an analysis result."},
    ],
}
