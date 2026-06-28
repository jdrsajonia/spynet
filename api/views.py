from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from analyzer import Analyzer

from api.serializers import (
    AnalysisInputSerializer,
    CompareQuerySerializer,
    SnapshotInputSerializer,
)
from api.utils.response import success_response

STUB = {"message": "not implemented"}


class AnalysisCreateView(APIView):
    _analyzer=Analyzer()
    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        url=serializer.validated_data["url"]
        data_analysis=self._analyzer.analyze(url)
        return success_response(data=data_analysis, meta={"analysis_id": 1}, status_code=201)


class AIAnalysisCreateView(APIView):
    def post(self, request):
        serializer = AnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(data=STUB, meta={"analysis_id": 1}, status_code=201)


class SnapshotAnalysisView(APIView):
    _analyzer=Analyzer()
    def post(self, request):
        serializer = SnapshotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url=serializer.validated_data["url"]
        data_analysis=self._analyzer.analyze_snapshot(url)
        return success_response(data=data_analysis, meta={"analysis_id": 1}, status_code=201)


class AnalysisDetailView(APIView):
    def get(self, request, pk):
        if pk < 1:
            raise NotFound("Analysis not found.")
        return success_response(data=STUB, meta={"analysis_id": pk}, status_code=200)


class AnalysisCompareView(APIView):
    def get(self, request):
        serializer = CompareQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return success_response(data=STUB, meta=serializer.validated_data, status_code=200)


class StatsView(APIView):
    def get(self, request):
        return success_response(data=STUB, status_code=200)
