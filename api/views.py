from collections import Counter

from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from analyzer import Analyzer
from api.models import Analysis
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
        result = _analyzer.analyze(url)

        analysis = Analysis.from_result(result)
        analysis.save()

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
        result = _analyzer.analyze_snapshot(snapshot_url)

        return success_response(data=result, status_code=201)


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
        names_a = {t["name"] for t in a.technologies}
        names_b = {t["name"] for t in b.technologies}

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
        analyses = Analysis.objects.all()
        tech_counter = Counter()
        category_counter = Counter()
        for analysis in analyses:
            for tech in analysis.technologies:
                tech_counter[tech["name"]] += 1
                category_counter[tech.get("category", "unknown")] += 1

        return success_response(
            data={
                "total_analyses": analyses.count(),
                "top_technologies": [
                    {"name": name, "count": count}
                    for name, count in tech_counter.most_common(10)
                ],
                "by_category": dict(category_counter),
            },
            status_code=200,
        )
