import time

from django.db.models import Count
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from analyzer import Analyzer
from api.models import Analysis, Technology
from api.persistence import persist_analysis, persist_snapshot
from api.serializers import (
    AnalysisInputSerializer,
    CompareQuerySerializer,
    SnapshotInputSerializer,
)
from api.utils.response import success_response

STUB = {"message": "not implemented"}

# Una sola instancia compartida: el Analyzer mantiene una requests.Session, el
# DetectorFactory y las firmas en memoria. No tiene estado por petición, así que
# es seguro reutilizarlo entre requests y evita reconstruirlo en cada llamada.
_analyzer = Analyzer()


class AnalysisCreateView(APIView):
    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        started = time.monotonic()
        result = _analyzer.analyze(url)
        duration_ms = int((time.monotonic() - started) * 1000)

        analysis = persist_analysis(result, triggered_by="api", duration_ms=duration_ms)
        return success_response(
            data=analysis.to_dict(),
            meta={"analysis_id": analysis.pk},
            status_code=201,
        )


class AIAnalysisCreateView(APIView):
    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(data=STUB, meta={"analysis_id": 1}, status_code=201)


class SnapshotAnalysisView(APIView):
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


class AnalysisCompareView(APIView):
    def get(self, request):
        serializer = CompareQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        id_a = serializer.validated_data["a"]
        id_b = serializer.validated_data["b"]

        analyses = {a.pk: a for a in Analysis.objects.filter(pk__in=(id_a, id_b))}
        if id_a not in analyses or id_b not in analyses:
            raise NotFound("One or both analyses were not found.")

        a, b = analyses[id_a], analyses[id_b]
        names_a = set(a.technologies.values_list("name", flat=True))
        names_b = set(b.technologies.values_list("name", flat=True))

        return success_response(
            data={
                "a": a.to_dict(),
                "b": b.to_dict(),
                "comparison": {
                    "shared_technologies": sorted(names_a & names_b),
                    "only_in_a": sorted(names_a - names_b),
                    "only_in_b": sorted(names_b - names_a),
                },
            },
            meta=serializer.validated_data,
            status_code=200,
        )


class StatsView(APIView):
    def get(self, request):
        top = (
            Technology.objects.values("name")
            .annotate(count=Count("id"))
            .order_by("-count", "name")[:10]
        )
        by_category = (
            Technology.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("category")
        )
        return success_response(
            data={
                "total_analyses": Analysis.objects.count(),
                "top_technologies": [
                    {"name": row["name"], "count": row["count"]} for row in top
                ],
                "by_category": {row["category"]: row["count"] for row in by_category},
            },
            status_code=200,
        )
