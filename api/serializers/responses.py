"""
Serializers de SALIDA: describen la forma de `data` en cada respuesta.

No se usan para validar ni para renderizar — las vistas devuelven los dicts de
`Model.to_dict()` directamente. Existen para que drf-spectacular pueda generar
el esquema OpenAPI. Si cambias un `to_dict()`, cambia el serializer de aquí.
"""
from rest_framework import serializers

from api.models import Analysis, Technology
from api.utils import error_codes

_STATUS = [c[0] for c in Analysis.STATUS_CHOICES]
_TRIGGER = [c[0] for c in Analysis.TRIGGER_CHOICES]
_CATEGORY = [c[0] for c in Technology.CATEGORY_CHOICES]


class TechnologySerializer(serializers.Serializer):
    """Una tecnología detectada. Espeja `Technology.to_dict()`."""
    name = serializers.CharField()
    category = serializers.ChoiceField(choices=_CATEGORY)
    version = serializers.CharField(allow_null=True)
    confidence = serializers.IntegerField(help_text="0–100.")
    evidence = serializers.CharField(allow_blank=True)


class AnalysisErrorSerializer(serializers.Serializer):
    """Fallo parcial de un servicio externo durante el análisis (no aborta el análisis)."""
    service = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    message = serializers.CharField(allow_blank=True)


class WhoisSerializer(serializers.Serializer):
    registrar = serializers.CharField(allow_null=True)
    registrant = serializers.CharField(allow_null=True)
    org = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    emails = serializers.ListField(child=serializers.CharField(), allow_null=True)
    dnssec = serializers.CharField(allow_null=True)
    status = serializers.ListField(child=serializers.CharField(), allow_null=True)
    creation_date = serializers.DateTimeField(allow_null=True)
    updated_date = serializers.DateTimeField(allow_null=True)
    expiration_date = serializers.DateTimeField(allow_null=True)
    domain_age_years = serializers.FloatField(allow_null=True)


class GeoSerializer(serializers.Serializer):
    country = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    isp = serializers.CharField(allow_null=True)
    org = serializers.CharField(allow_null=True)
    ip = serializers.IPAddressField(allow_null=True)
    lat = serializers.FloatField(allow_null=True)
    lon = serializers.FloatField(allow_null=True)
    reverse_dns = serializers.CharField(allow_null=True)


class WaybackSnapshotSerializer(serializers.Serializer):
    timestamp = serializers.CharField(help_text="Marca de Wayback, `YYYYMMDDhhmmss`.")
    url = serializers.URLField()
    technologies = TechnologySerializer(many=True)


class WaybackResultSerializer(serializers.Serializer):
    snapshot_count = serializers.IntegerField()
    archive_pages = serializers.IntegerField(allow_null=True)
    first_snapshot_at = serializers.DateTimeField(allow_null=True)
    last_snapshot_at = serializers.DateTimeField(allow_null=True)
    snapshots = WaybackSnapshotSerializer(many=True)


class AnalysisSerializer(serializers.Serializer):
    """Un análisis completo. Espeja `Analysis.to_dict()`."""
    id = serializers.IntegerField()
    url = serializers.URLField()
    domain = serializers.CharField()
    status = serializers.ChoiceField(choices=_STATUS)
    triggered_by = serializers.ChoiceField(choices=_TRIGGER)
    duration_ms = serializers.IntegerField(allow_null=True)
    analyzed_at = serializers.DateTimeField()
    technologies = TechnologySerializer(many=True)
    dns = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        allow_null=True,
        help_text="Registros DNS por tipo, p. ej. `{\"A\": [\"1.2.3.4\"], \"MX\": [...]}`.",
    )
    whois = WhoisSerializer(allow_null=True)
    geo = GeoSerializer(allow_null=True)
    tls = serializers.JSONField(allow_null=True, help_text="Certificado TLS/SSL.")
    security = serializers.JSONField(allow_null=True, help_text="Nota y hallazgos de seguridad.")
    email_security = serializers.JSONField(allow_null=True, help_text="SPF / DMARC / DNSSEC.")
    wayback = WaybackResultSerializer(allow_null=True)
    errors = AnalysisErrorSerializer(many=True)
    tags = serializers.DictField(child=serializers.CharField())


class AnalysisListItemSerializer(serializers.Serializer):
    """Fila del listado paginado: resumen, sin el detalle del análisis."""
    id = serializers.IntegerField()
    domain = serializers.CharField()
    url = serializers.URLField()
    status = serializers.ChoiceField(choices=_STATUS)
    triggered_by = serializers.ChoiceField(choices=_TRIGGER)
    analyzed_at = serializers.DateTimeField()
    technologies_count = serializers.IntegerField()


# ── bloques `meta` ────────────────────────────────────────────────────────────

class PageMetaSerializer(serializers.Serializer):
    """`meta` del listado paginado."""
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    total = serializers.IntegerField()
    page_size = serializers.IntegerField()


class AnalysisIdMetaSerializer(serializers.Serializer):
    """`meta` de las vistas que devuelven un único análisis persistido."""
    analysis_id = serializers.IntegerField()


class WaybackMetaSerializer(serializers.Serializer):
    """`meta` de la carga de Wayback."""
    analysis_id = serializers.IntegerField()
    status = serializers.CharField(required=False, help_text="`empty` si no hubo capturas.")


class CompareIdsMetaSerializer(serializers.Serializer):
    """`meta` de las comparaciones: los ids de los dos análisis usados."""
    a = serializers.IntegerField()
    b = serializers.IntegerField()


class DomainMetaSerializer(serializers.Serializer):
    """`meta` del histórico por dominio."""
    domain = serializers.CharField()
    count = serializers.IntegerField()


class HistoricalSerializer(serializers.Serializer):
    """Respuesta de `POST /analyses/historical/` cuando el dominio no tiene historial."""
    url = serializers.URLField()
    snapshots = serializers.ListField(child=serializers.JSONField(), help_text="Vacío.")


class DomainHistoryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=_STATUS)
    triggered_by = serializers.ChoiceField(choices=_TRIGGER)
    analyzed_at = serializers.DateTimeField()
    technologies = TechnologySerializer(many=True)


# ── comparación ───────────────────────────────────────────────────────────────

class SharedTechnologySerializer(serializers.Serializer):
    name = serializers.CharField()
    category = serializers.ChoiceField(choices=_CATEGORY)
    confidence_a = serializers.IntegerField()
    confidence_b = serializers.IntegerField()


class OnlyInTechnologySerializer(serializers.Serializer):
    name = serializers.CharField()
    category = serializers.ChoiceField(choices=_CATEGORY)
    confidence = serializers.IntegerField()


class ComparisonSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Tecnologías distintas en la unión de A y B.")
    shared_technologies = SharedTechnologySerializer(many=True)
    only_in_a = OnlyInTechnologySerializer(many=True)
    only_in_b = OnlyInTechnologySerializer(many=True)


class CompareSerializer(serializers.Serializer):
    a = AnalysisSerializer()
    b = AnalysisSerializer()
    comparison = ComparisonSerializer()


# ── estadísticas ──────────────────────────────────────────────────────────────

class TopTechnologySerializer(serializers.Serializer):
    name = serializers.CharField()
    category = serializers.ChoiceField(choices=_CATEGORY)
    count = serializers.IntegerField()


class ActivityPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class StatsSerializer(serializers.Serializer):
    total_analyses = serializers.IntegerField()
    unique_domains = serializers.IntegerField()
    total_detections = serializers.IntegerField()
    avg_analysis_time_seconds = serializers.FloatField(allow_null=True)
    avg_confidence = serializers.FloatField(allow_null=True, help_text="0–100.")
    top_technologies = TopTechnologySerializer(many=True, help_text="Las 20 más detectadas.")
    by_category = serializers.DictField(child=serializers.IntegerField())
    activity = ActivityPointSerializer(many=True, help_text="Análisis por día.")


# ── asistente de IA ───────────────────────────────────────────────────────────

class AIQuestionSerializer(serializers.Serializer):
    """Entrada de `POST /ai-analyses/`."""
    question = serializers.CharField(help_text="Pregunta en lenguaje natural.")
    analysis = serializers.JSONField(help_text="El objeto `data` de un análisis previo.")
    history = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        help_text="Turnos anteriores de la conversación.",
    )


class AIAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()
    provider = serializers.CharField(help_text="`gemini`, `fallback` o `error`.")
    status = serializers.CharField()


# ── error ─────────────────────────────────────────────────────────────────────

class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=list(error_codes.ALL))
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    """Toda respuesta de error de la API tiene esta forma."""
    success = serializers.BooleanField(default=False)
    data = serializers.JSONField(allow_null=True, default=None)
    error = ErrorDetailSerializer()
    meta = serializers.DictField(
        help_text="En `VALIDATION_ERROR` contiene `fields` con los errores por campo.",
    )
