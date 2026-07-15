import time
from collections import Counter

from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from whois import extract_domain

from analyzer import Analyzer
from api.models import Analysis, Domain, Technology, WaybackResult
from api.persistence import persist_analysis, persist_history, persist_snapshot, persist_wayback
from api.serializers import (
    AnalysisInputSerializer,
    CompareQuerySerializer,
    CompareUrlSerializer,
    SnapshotInputSerializer,
)
from api.serializers.responses import (
    AIAnswerSerializer,
    AIQuestionSerializer,
    AnalysisIdMetaSerializer,
    AnalysisListItemSerializer,
    AnalysisSerializer,
    CompareIdsMetaSerializer,
    CompareSerializer,
    DomainHistoryItemSerializer,
    DomainMetaSerializer,
    HistoricalSerializer,
    PageMetaSerializer,
    StatsSerializer,
    WaybackMetaSerializer,
    WaybackResultSerializer,
)
from api.ai_assistant import get_ai_response
from api.utils import error_codes, schema
from api.utils.response import error_response, success_response

STUB = {"message": "not implemented"}

# Una sola instancia compartida: el Analyzer mantiene una requests.Session, el
# DetectorFactory y las firmas en memoria. No tiene estado por petición, así que
# es seguro reutilizarlo entre requests y evita reconstruirlo en cada llamada.
_analyzer = Analyzer()


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_int(value, default):
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _resolve_or_analyze(url: str) -> Analysis:
    """
    Opción B: devuelve el último análisis guardado del dominio de `url`;
    si nunca se ha analizado, lo analiza en vivo y lo persiste.
    """
    domain_name = extract_domain(url)
    analysis = (
        Analysis.objects.filter(domain__name=domain_name)
        .order_by("-analyzed_at")
        .first()
    )
    if analysis is None:
        # Comparar no usa el histórico → se excluye Wayback para no pagar su latencia.
        result = _analyzer.analyze(url, include_wayback=False)
        analysis = persist_analysis(result, triggered_by="api")
    return analysis


def _tech_map(analysis: Analysis) -> dict:
    """{nombre: {category, confidence}} de las tecnologías en vivo del análisis."""
    return {
        t["name"]: {"category": t["category"], "confidence": t["confidence"]}
        for t in analysis.technologies.values("name", "category", "confidence")
    }


def _compare_payload(a: Analysis, b: Analysis) -> dict:
    techs_a, techs_b = _tech_map(a), _tech_map(b)
    names_a, names_b = set(techs_a), set(techs_b)

    shared = [
        {
            "name": name,
            "category": techs_a[name]["category"],
            "confidence_a": techs_a[name]["confidence"],
            "confidence_b": techs_b[name]["confidence"],
        }
        for name in sorted(names_a & names_b)
    ]
    only_a = [
        {"name": n, "category": techs_a[n]["category"], "confidence": techs_a[n]["confidence"]}
        for n in sorted(names_a - names_b)
    ]
    only_b = [
        {"name": n, "category": techs_b[n]["category"], "confidence": techs_b[n]["confidence"]}
        for n in sorted(names_b - names_a)
    ]
    return {
        "a": a.to_dict(),
        "b": b.to_dict(),
        "comparison": {
            "total": len(names_a | names_b),
            "shared_technologies": shared,
            "only_in_a": only_a,
            "only_in_b": only_b,
        },
    }


# ── vistas ────────────────────────────────────────────────────────────────────

@extend_schema_view(
    post=extend_schema(
        tags=["analyses"],
        summary="Analyze a URL live",
        description=(
            "Fetches the URL, detects its technology stack and persists the result, "
            "which then becomes retrievable, comparable and counted in `/stats/`.\n\n"
            "Wayback snapshots are **not** included: they are the slow part. Load them "
            "afterwards with `POST /analyses/{id}/wayback/`.\n\n"
            "Rate limited to 10/min per IP."
        ),
        request=AnalysisInputSerializer,
        responses={
            201: schema.envelope("AnalysisCreateResponse", AnalysisSerializer(), AnalysisIdMetaSerializer()),
            400: schema.VALIDATION,
            429: schema.RATE_LIMITED,
            502: schema.UPSTREAM,
        },
    ),
    get=extend_schema(
        tags=["analyses"],
        # Sin esto colisiona con el operationId de GET /analyses/{id}/.
        operation_id="analyses_list",
        summary="List saved analyses",
        description="Newest first. Paginated; `meta` carries the page counters.",
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, description="1-based. Defaults to 1."),
            OpenApiParameter(
                "page_size", OpenApiTypes.INT,
                description="Defaults to 20, capped at 100.",
            ),
        ],
        responses={
            200: schema.envelope("AnalysisListResponse", AnalysisListItemSerializer(many=True), PageMetaSerializer()),
            429: schema.RATE_LIMITED,
        },
    ),
)
class AnalysisCreateView(APIView):
    def get_throttles(self):
        # El POST dispara análisis en vivo → throttle estricto; el GET (listado) no.
        if self.request.method == "POST":
            self.throttle_scope = "analyze"
        return super().get_throttles()

    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        started = time.monotonic()
        # Wayback se excluye aquí (es el cuello de botella) y se carga aparte,
        # en segundo plano, vía POST /analyses/<id>/wayback/.
        result = _analyzer.analyze(url, include_wayback=False)
        duration_ms = int((time.monotonic() - started) * 1000)

        analysis = persist_analysis(result, triggered_by="api", duration_ms=duration_ms)
        return success_response(
            data=analysis.to_dict(),
            meta={"analysis_id": analysis.pk},
            status_code=201,
        )

    def get(self, request):
        page = _safe_int(request.query_params.get("page"), 1)
        page_size = min(_safe_int(request.query_params.get("page_size"), 20), 100)

        qs = (
            Analysis.objects
            # historical/snapshot cuelgan sus tecnologías del WaybackSnapshot, no
            # del Analysis, así que aquí aparecerían con 0 → se excluyen del listado.
            .exclude(triggered_by__in=["historical", "snapshot"])
            .select_related("domain")
            .annotate(technologies_count=Count("technologies"))
            .order_by("-analyzed_at")
        )
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        data = [
            {
                "id": a.pk,
                "domain": a.domain.name,
                "url": a.source_url,
                "status": a.status,
                "triggered_by": a.triggered_by,
                "analyzed_at": a.analyzed_at.isoformat(),
                "technologies_count": a.technologies_count,
            }
            for a in page_obj
        ]
        return success_response(
            data=data,
            meta={
                "page": page_obj.number,
                "pages": paginator.num_pages,
                "total": paginator.count,
                "page_size": page_size,
            },
            status_code=200,
        )


@extend_schema(
    tags=["ai"],
    summary="Ask the AI assistant about an analysis",
    description=(
        "Answers a natural-language question about an analysis you already ran. "
        "Pass the analysis object back verbatim — the API does not look it up by id.\n\n"
        "If the Gemini API key is missing or the call fails, it degrades to a local "
        "fallback answer with `provider` set to `fallback` or `error`, still HTTP 200.\n\n"
        "Rate limited to 15/min per IP."
    ),
    request=AIQuestionSerializer,
    responses={
        200: schema.envelope("AIAnswerResponse", AIAnswerSerializer()),
        400: schema.error("`MISSING_QUESTION` o `MISSING_ANALYSIS`."),
        429: schema.RATE_LIMITED,
    },
)
class AIAnalysisCreateView(APIView):
    throttle_scope = "ai"  # protege la cuota/costo de la API de Gemini

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        analysis = request.data.get("analysis")
        history = request.data.get("history", [])

        if not question:
            return error_response(error_codes.MISSING_QUESTION, "question is required.", 400)
        if not analysis or not isinstance(analysis, dict):
            return error_response(error_codes.MISSING_ANALYSIS, "analysis object is required.", 400)

        try:
            result = get_ai_response(question, analysis, history)
        except Exception:
            result = {
                "answer": "Lo siento, ocurrió un error procesando tu pregunta. Intenta reformularla.",
                "provider": "error",
                "status": "error",
            }
        return success_response(data=result, status_code=200)


@extend_schema(
    tags=["analyses"],
    summary="Analyze a single Wayback snapshot",
    description=(
        "Passive analysis of one archived capture. `snapshot_url` must start with "
        "`https://web.archive.org/`. The result is persisted with "
        "`triggered_by = snapshot`.\n\n"
        "Rate limited to 10/min per IP."
    ),
    request=SnapshotInputSerializer,
    responses={
        201: schema.envelope("SnapshotAnalysisResponse", AnalysisSerializer(), AnalysisIdMetaSerializer()),
        400: schema.VALIDATION,
        404: schema.error("La captura no se pudo descargar (`NOT_FOUND`)."),
        429: schema.RATE_LIMITED,
        502: schema.UPSTREAM,
    },
)
class SnapshotAnalysisView(APIView):
    throttle_scope = "analyze"

    def post(self, request):
        serializer = SnapshotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        snapshot_url = serializer.validated_data["snapshot_url"]
        started = time.monotonic()
        result = _analyzer.analyze_snapshot(snapshot_url)
        duration_ms = int((time.monotonic() - started) * 1000)

        if result is None:
            raise NotFound("The snapshot could not be fetched.")

        analysis = persist_snapshot(result, duration_ms=duration_ms)
        return success_response(
            data=analysis.to_dict(),
            meta={"analysis_id": analysis.pk},
            status_code=201,
        )


@extend_schema(
    tags=["analyses"],
    summary="Analyze a domain across its Wayback history",
    description=(
        "Downloads and analyzes roughly 12 archived captures of the domain to show how "
        "its stack evolved. **Slow** — expect tens of seconds.\n\n"
        "If the domain has no captures, returns `200` with an empty `snapshots` list "
        "and persists nothing. Otherwise returns `201` with the persisted analysis.\n\n"
        "Rate limited to 10/min per IP."
    ),
    request=AnalysisInputSerializer,
    responses={
        200: schema.envelope("HistoricalEmptyResponse", HistoricalSerializer()),
        201: schema.envelope("HistoricalAnalysisResponse", AnalysisSerializer(), AnalysisIdMetaSerializer()),
        400: schema.VALIDATION,
        429: schema.RATE_LIMITED,
        502: schema.UPSTREAM,
    },
)
class HistoricalAnalysisView(APIView):
    throttle_scope = "analyze"  # pesado: descarga y analiza ~12 capturas

    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        started = time.monotonic()
        result = _analyzer.analyze_history(url)
        duration_ms = int((time.monotonic() - started) * 1000)

        if not result["snapshots"]:
            # Sin historial: estado vacío limpio, sin persistir un registro vacío.
            return success_response(
                data={"url": url, "snapshots": []},
                meta={"snapshots": 0},
                status_code=200,
            )

        analysis = persist_history(result, duration_ms=duration_ms)
        return success_response(
            data=analysis.to_dict(),
            meta={"analysis_id": analysis.pk},
            status_code=201,
        )


@extend_schema(
    tags=["analyses"],
    summary="Retrieve a saved analysis",
    parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="Analysis id."),
    ],
    responses={
        200: schema.envelope("AnalysisDetailResponse", AnalysisSerializer(), AnalysisIdMetaSerializer()),
        404: schema.NOT_FOUND,
        429: schema.RATE_LIMITED,
    },
)
class AnalysisDetailView(APIView):
    def get(self, request, pk):
        try:
            analysis = Analysis.objects.get(pk=pk)
        except Analysis.DoesNotExist:
            raise NotFound("Analysis not found.")
        return success_response(
            data=analysis.to_dict(),
            meta={"analysis_id": analysis.pk},
            status_code=200,
        )


@extend_schema(
    tags=["analyses"],
    summary="Load Wayback snapshots for an analysis",
    description=(
        "Fetches the archived captures for the analysis's URL and attaches them to it. "
        "`POST /analyses/` skips this on purpose because it is the slow part.\n\n"
        "**Idempotent**: if snapshots were already loaded, returns `200` with the stored "
        "result instead of hitting web.archive.org again. If the domain has no captures, "
        "returns `200` with `data: null` and `meta.status = \"empty\"`, so the client can "
        "decide whether to retry. A fresh successful load returns `201`.\n\n"
        "Rate limited to 10/min per IP."
    ),
    request=None,
    parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH, description="Analysis id."),
    ],
    responses={
        200: schema.envelope("WaybackExistingResponse", WaybackResultSerializer(allow_null=True), WaybackMetaSerializer()),
        201: schema.envelope("WaybackCreatedResponse", WaybackResultSerializer(), AnalysisIdMetaSerializer()),
        404: schema.NOT_FOUND,
        429: schema.RATE_LIMITED,
        502: schema.UPSTREAM,
    },
)
class AnalysisWaybackView(APIView):
    throttle_scope = "analyze"  # pega a web.archive.org

    def post(self, request, pk):
        try:
            analysis = Analysis.objects.get(pk=pk)
        except Analysis.DoesNotExist:
            raise NotFound("Analysis not found.")

        # Idempotente: si ya se cargó con éxito, devolverlo sin re-pegarle a Wayback.
        existing = WaybackResult.objects.filter(analysis=analysis).first()
        if existing and existing.snapshot_count > 0:
            return success_response(data=existing.to_dict(), meta={"analysis_id": pk}, status_code=200)
        if existing:
            existing.delete()  # intento previo vacío → reintentar limpio

        wayback = _analyzer.wayback(analysis.source_url)
        if not wayback or not wayback.get("snapshots"):
            # Vacío o falló: el frontend decide si reintentar.
            return success_response(data=None, meta={"analysis_id": pk, "status": "empty"}, status_code=200)

        result = persist_wayback(analysis, wayback)
        return success_response(data=result.to_dict(), meta={"analysis_id": pk}, status_code=201)


@extend_schema_view(
    get=extend_schema(
        tags=["analyses"],
        summary="Compare two saved analyses by id",
        description="Both analyses must already exist. `a` and `b` must differ.",
        parameters=[CompareQuerySerializer],
        responses={
            200: schema.envelope("CompareByIdResponse", CompareSerializer(), CompareIdsMetaSerializer()),
            400: schema.VALIDATION,
            404: schema.error("Uno o ambos análisis no existen (`NOT_FOUND`)."),
            429: schema.RATE_LIMITED,
        },
    ),
    post=extend_schema(
        tags=["analyses"],
        summary="Compare two sites by URL",
        description=(
            "Each URL resolves to the most recent stored analysis of its domain. If a "
            "domain has never been analyzed, it is analyzed live and persisted first — "
            "so this can be slow, and `meta` returns the ids that were used.\n\n"
            "Rate limited to 10/min per IP."
        ),
        request=CompareUrlSerializer,
        responses={
            200: schema.envelope("CompareByUrlResponse", CompareSerializer(), CompareIdsMetaSerializer()),
            400: schema.VALIDATION,
            429: schema.RATE_LIMITED,
            502: schema.UPSTREAM,
        },
    ),
)
class AnalysisCompareView(APIView):
    def get_throttles(self):
        # El POST puede analizar en vivo (resolver-o-analizar) → throttle estricto.
        if self.request.method == "POST":
            self.throttle_scope = "analyze"
        return super().get_throttles()

    def get(self, request):
        # Comparar dos análisis existentes por id.
        serializer = CompareQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        id_a = serializer.validated_data["a"]
        id_b = serializer.validated_data["b"]

        analyses = {a.pk: a for a in Analysis.objects.filter(pk__in=(id_a, id_b))}
        if id_a not in analyses or id_b not in analyses:
            raise NotFound("One or both analyses were not found.")

        return success_response(
            data=_compare_payload(analyses[id_a], analyses[id_b]),
            meta=serializer.validated_data,
            status_code=200,
        )

    def post(self, request):
        # Comparar dos sitios por URL (opción B: resolver al último análisis o analizar).
        serializer = CompareUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        a = _resolve_or_analyze(serializer.validated_data["url_a"])
        b = _resolve_or_analyze(serializer.validated_data["url_b"])

        return success_response(
            data=_compare_payload(a, b),
            meta={"a": a.pk, "b": b.pk},
            status_code=200,
        )


@extend_schema(
    tags=["domains"],
    summary="List every analysis of a domain",
    description="Newest first. Returns `404` if the domain has never been analyzed.",
    parameters=[
        OpenApiParameter(
            "name", OpenApiTypes.STR, OpenApiParameter.PATH,
            description="Bare domain name, e.g. `github.com`.",
        ),
    ],
    responses={
        200: schema.envelope("DomainHistoryResponse", DomainHistoryItemSerializer(many=True), DomainMetaSerializer()),
        404: schema.NOT_FOUND,
        429: schema.RATE_LIMITED,
    },
)
class DomainHistoryView(APIView):
    def get(self, request, name):
        analyses = Analysis.objects.filter(domain__name=name).order_by("-analyzed_at")
        if not analyses.exists():
            raise NotFound(f"No analyses found for domain '{name}'.")

        data = [
            {
                "id": a.pk,
                "status": a.status,
                "triggered_by": a.triggered_by,
                "analyzed_at": a.analyzed_at.isoformat(),
                "technologies": [t.to_dict() for t in a.technologies.all()],
            }
            for a in analyses
        ]
        return success_response(
            data=data,
            meta={"domain": name, "count": len(data)},
            status_code=200,
        )


@extend_schema(
    tags=["stats"],
    summary="Aggregate stats across all stored analyses",
    description="Powers the dashboard. Averages are `null` while there is no data yet.",
    responses={
        200: schema.envelope("StatsResponse", StatsSerializer()),
        429: schema.RATE_LIMITED,
    },
)
class StatsView(APIView):
    def get(self, request):
        avg_ms = Analysis.objects.aggregate(v=Avg("duration_ms"))["v"]
        avg_conf = Technology.objects.aggregate(v=Avg("confidence"))["v"]

        # Detecciones deduplicadas por dominio: una tecnología cuenta UNA sola vez
        # por dominio, sin importar cuántas veces se reanalizó ese dominio. Así
        # reanalizar Facebook 100 veces no infla "php" a 100. Solo se cuentan
        # análisis en vivo (analysis__isnull=False); las tecnologías de snapshots
        # históricos (Wayback) no alimentan el dashboard.
        # Las tres métricas de abajo (top_technologies, by_category,
        # total_detections) se derivan de esta misma base, así que sus totales
        # siempre cuadran y el donut queda coherente.
        detections = (
            Technology.objects
            .filter(analysis__isnull=False)
            .values_list("analysis__domain_id", "name", "category")
            .distinct()
        )

        by_name = Counter()      # (name, category) -> nº de dominios distintos
        by_category = Counter()  # category         -> nº de detecciones únicas
        for _domain_id, name, category in detections:
            by_name[(name, category)] += 1
            by_category[category] += 1

        top = sorted(by_name.items(), key=lambda kv: (-kv[1], kv[0][0]))[:20]

        activity = (
            Analysis.objects.annotate(day=TruncDate("analyzed_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return success_response(
            data={
                "total_analyses": Analysis.objects.count(),
                "unique_domains": Domain.objects.count(),
                "total_detections": sum(by_category.values()),
                "avg_analysis_time_seconds": round(avg_ms / 1000, 2) if avg_ms else None,
                "avg_confidence": round(avg_conf, 1) if avg_conf is not None else None,
                "top_technologies": [
                    {"name": name, "category": category, "count": count}
                    for (name, category), count in top
                ],
                "by_category": dict(by_category),
                "activity": [
                    {"date": row["day"].isoformat(), "count": row["count"]}
                    for row in activity
                ],
            },
            status_code=200,
        )
