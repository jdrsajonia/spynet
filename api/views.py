import time

from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
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
from api.ai_assistant import get_ai_response
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
            Analysis.objects.select_related("domain")
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


class AIAnalysisCreateView(APIView):
    throttle_scope = "ai"  # protege la cuota/costo de la API de Gemini

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        analysis = request.data.get("analysis")
        history = request.data.get("history", [])

        if not question:
            return error_response("MISSING_QUESTION", "question is required.", 400)
        if not analysis or not isinstance(analysis, dict):
            return error_response("MISSING_ANALYSIS", "analysis object is required.", 400)

        try:
            result = get_ai_response(question, analysis, history)
        except Exception:
            result = {
                "answer": "Lo siento, ocurrió un error procesando tu pregunta. Intenta reformularla.",
                "provider": "error",
                "status": "error",
            }
        return success_response(data=result, status_code=200)


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


class StatsView(APIView):
    def get(self, request):
        avg_ms = Analysis.objects.aggregate(v=Avg("duration_ms"))["v"]
        avg_conf = Technology.objects.aggregate(v=Avg("confidence"))["v"]

        top = (
            Technology.objects.values("name", "category")
            .annotate(count=Count("id"))
            .order_by("-count", "name")[:20]
        )
        by_category = (
            Technology.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("category")
        )
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
                "total_detections": Technology.objects.count(),
                "avg_analysis_time_seconds": round(avg_ms / 1000, 2) if avg_ms else None,
                "avg_confidence": round(avg_conf, 1) if avg_conf is not None else None,
                "top_technologies": [
                    {"name": row["name"], "category": row["category"], "count": row["count"]}
                    for row in top
                ],
                "by_category": {row["category"]: row["count"] for row in by_category},
                "activity": [
                    {"date": row["day"].isoformat(), "count": row["count"]}
                    for row in activity
                ],
            },
            status_code=200,
        )
