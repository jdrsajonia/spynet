import pytest
from rest_framework.test import APIClient

from api.models import Analysis, Domain, Technology, WaybackResult
from api.persistence import persist_analysis
from api.utils import error_codes

pytestmark = pytest.mark.django_db


FAKE_TECHS = [
    {"name": "React", "category": "frontend", "version": None, "confidence": 100, "evidence": "html"},
    {"name": "Nginx", "category": "server", "version": "1.25.3", "confidence": 60, "evidence": "header"},
]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture(autouse=True)
def mock_analyzer(monkeypatch):
    """Reemplaza el Analyzer compartido para que los tests no salgan a la red."""
    def fake_analyze(url, include_wayback=True):
        result = {
            "url": url,
            "technologies": FAKE_TECHS,
            "dns": {"A": ["1.2.3.4"], "MX": ["10 mail.example.com"]},
            "whois": None,
            "geo": None,
        }
        if include_wayback:
            result["wayback"] = None  # ausente si se excluye (Compare)
        return result

    def fake_snapshot(url):
        return {"snapshot_url": url, "technologies": FAKE_TECHS}

    def fake_history(url):
        return {
            "url": url, "archive_pages": 5,
            "snapshots": [
                {"timestamp": "20200101000000", "url": "https://web.archive.org/web/20200101000000/https://x.com/", "technologies": [FAKE_TECHS[0]]},
                {"timestamp": "20210101000000", "url": "https://web.archive.org/web/20210101000000/https://x.com/", "technologies": FAKE_TECHS},
            ],
        }

    def fake_wayback(url):
        return {
            "archive_pages": 5,
            "snapshots": [
                {"timestamp": "20200101000000", "url": "https://web.archive.org/web/20200101000000/https://example.com/"},
                {"timestamp": "20210101000000", "url": "https://web.archive.org/web/20210101000000/https://example.com/"},
            ],
        }

    monkeypatch.setattr("api.views._analyzer.analyze", fake_analyze)
    monkeypatch.setattr("api.views._analyzer.analyze_snapshot", fake_snapshot)
    monkeypatch.setattr("api.views._analyzer.analyze_history", fake_history)
    monkeypatch.setattr("api.views._analyzer.wayback", fake_wayback)


def make_analysis(url="https://example.com", techs=None):
    return persist_analysis(
        {
            "url": url,
            "technologies": techs if techs is not None else FAKE_TECHS,
            "dns": None, "whois": None, "geo": None, "wayback": None,
        },
        triggered_by="api",
    )


def assert_envelope(body):
    assert set(body.keys()) == {"success", "data", "error", "meta"}


class TestEnvelope:
    def test_success_envelope_shape(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        assert resp.status_code == 201
        body = resp.json()
        assert_envelope(body)
        assert body["success"] is True
        assert body["error"] is None
        assert body["data"]["url"] == "https://example.com"
        assert body["data"]["technologies"] == FAKE_TECHS
        assert isinstance(body["meta"]["analysis_id"], int)

    def test_error_envelope_shape(self, client):
        resp = client.post("/api/v1/analyses/", {}, format="json")
        assert resp.status_code == 400
        body = resp.json()
        assert_envelope(body)
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["code"] == error_codes.VALIDATION_ERROR


class TestAnalysesCreate:
    def test_create_persists_normalized_graph(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        assert resp.status_code == 201
        analysis = Analysis.objects.get(pk=resp.json()["meta"]["analysis_id"])
        assert Domain.objects.filter(name="example.com").exists()
        assert analysis.technologies.count() == 2
        assert analysis.status == "partial"
        # Wayback se excluye del análisis principal (carga diferida) → no es error.
        assert set(analysis.errors.values_list("service", flat=True)) == {"whois", "geo"}
        assert analysis.dns_result.records.count() == 2

    def test_dns_mx_priority_is_parsed(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        analysis = Analysis.objects.get(pk=resp.json()["meta"]["analysis_id"])
        mx = analysis.dns_result.records.get(record_type="MX")
        assert mx.priority == 10
        assert mx.value == "mail.example.com"

    def test_url_normalized_without_scheme(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "github.com"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["data"]["url"] == "https://github.com"

    def test_missing_url_is_validation_error(self, client):
        resp = client.post("/api/v1/analyses/", {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR

    def test_invalid_url_is_validation_error(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "not a url"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR


class TestAnalysesList:
    def test_list_paginated(self, client):
        make_analysis(url="https://a.com")
        make_analysis(url="https://b.com")
        resp = client.get("/api/v1/analyses/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        assert len(body["data"]) == 2
        assert {"id", "domain", "url", "status", "technologies_count"} <= set(body["data"][0].keys())

    def test_list_respects_page_size(self, client):
        for i in range(3):
            make_analysis(url=f"https://s{i}.com")
        resp = client.get("/api/v1/analyses/?page_size=2")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2
        assert resp.json()["meta"]["pages"] == 2


class TestAIAnalyses:
    def test_create_ok(self, client):
        resp = client.post("/api/v1/ai-analyses/", {"url": "example.com"}, format="json")
        assert resp.status_code == 201

    def test_missing_url(self, client):
        resp = client.post("/api/v1/ai-analyses/", {}, format="json")
        assert resp.status_code == 400


class TestSnapshot:
    def test_create_persists_snapshot_record(self, client):
        url = "https://web.archive.org/web/20200101000000/https://example.com"
        resp = client.post("/api/v1/analyses/snapshot/", {"snapshot_url": url}, format="json")
        assert resp.status_code == 201
        analysis = Analysis.objects.get(pk=resp.json()["meta"]["analysis_id"])
        assert analysis.triggered_by == "snapshot"
        assert analysis.technologies.count() == 0
        assert analysis.wayback_result.snapshots.get().technologies.count() == 2

    def test_rejects_non_wayback_url(self, client):
        resp = client.post(
            "/api/v1/analyses/snapshot/", {"snapshot_url": "https://example.com"}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR

    def test_missing_snapshot_url(self, client):
        resp = client.post("/api/v1/analyses/snapshot/", {}, format="json")
        assert resp.status_code == 400


class TestHistorical:
    def test_analyzes_all_snapshots(self, client):
        resp = client.post("/api/v1/analyses/historical/", {"url": "x.com"}, format="json")
        assert resp.status_code == 201
        analysis = Analysis.objects.get(pk=resp.json()["meta"]["analysis_id"])
        assert analysis.triggered_by == "historical"
        snaps = analysis.wayback_result.snapshots.all()
        assert snaps.count() == 2
        # Las tecnologías cuelgan de cada snapshot (1 + 2 = 3 en el mock).
        assert sum(s.technologies.count() for s in snaps) == 3

    def test_empty_history_not_persisted(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.views._analyzer.analyze_history",
            lambda url: {"url": url, "archive_pages": 0, "snapshots": []},
        )
        resp = client.post("/api/v1/analyses/historical/", {"url": "x.com"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["data"]["snapshots"] == []
        assert not Analysis.objects.exists()

    def test_missing_url(self, client):
        resp = client.post("/api/v1/analyses/historical/", {}, format="json")
        assert resp.status_code == 400


class TestDetail:
    def test_retrieve_ok(self, client):
        analysis = make_analysis()
        resp = client.get(f"/api/v1/analyses/{analysis.pk}/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"] == {"analysis_id": analysis.pk}
        assert body["data"]["id"] == analysis.pk
        assert {t["name"] for t in body["data"]["technologies"]} == {"React", "Nginx"}

    def test_unknown_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/999999/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND

    def test_non_integer_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/abc/")
        assert resp.status_code == 404

    def test_zero_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/0/")
        assert resp.status_code == 404


class TestWayback:
    def _create(self, client):
        r = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        return r.json()["meta"]["analysis_id"]

    def test_loads_and_attaches(self, client):
        aid = self._create(client)
        resp = client.post(f"/api/v1/analyses/{aid}/wayback/")
        assert resp.status_code == 201
        assert len(resp.json()["data"]["snapshots"]) == 2
        assert Analysis.objects.get(pk=aid).wayback_result.snapshots.count() == 2

    def test_idempotent_no_duplicates(self, client):
        aid = self._create(client)
        client.post(f"/api/v1/analyses/{aid}/wayback/")
        resp = client.post(f"/api/v1/analyses/{aid}/wayback/")
        assert resp.status_code == 200
        assert Analysis.objects.get(pk=aid).wayback_result.snapshots.count() == 2

    def test_empty_returns_null(self, client, monkeypatch):
        aid = self._create(client)
        monkeypatch.setattr("api.views._analyzer.wayback", lambda url: {"archive_pages": 0, "snapshots": []})
        resp = client.post(f"/api/v1/analyses/{aid}/wayback/")
        assert resp.status_code == 200
        assert resp.json()["data"] is None

    def test_unknown_analysis_is_not_found(self, client):
        resp = client.post("/api/v1/analyses/999999/wayback/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND


class TestDomainHistory:
    def test_history_ok(self, client):
        make_analysis(url="https://hist.com", techs=[FAKE_TECHS[0]])
        make_analysis(url="https://hist.com", techs=FAKE_TECHS)
        resp = client.get("/api/v1/domains/hist.com/analyses/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"] == {"domain": "hist.com", "count": 2}
        assert len(body["data"]) == 2

    def test_unknown_domain_is_not_found(self, client):
        resp = client.get("/api/v1/domains/nope.com/analyses/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND


class TestCompareById:
    def test_compare_ok(self, client):
        a = make_analysis(url="https://a.com", techs=[FAKE_TECHS[0]])
        b = make_analysis(url="https://b.com", techs=[FAKE_TECHS[1]])
        resp = client.get(f"/api/v1/analyses/compare/?a={a.pk}&b={b.pk}")
        assert resp.status_code == 200
        comp = resp.json()["data"]["comparison"]
        assert comp["total"] == 2
        assert [t["name"] for t in comp["only_in_a"]] == ["React"]
        assert [t["name"] for t in comp["only_in_b"]] == ["Nginx"]
        assert comp["shared_technologies"] == []

    def test_shared_includes_both_confidences(self, client):
        a = make_analysis(url="https://a.com", techs=[{"name": "React", "category": "frontend", "confidence": 90, "evidence": "x"}])
        b = make_analysis(url="https://b.com", techs=[{"name": "React", "category": "frontend", "confidence": 70, "evidence": "y"}])
        resp = client.get(f"/api/v1/analyses/compare/?a={a.pk}&b={b.pk}")
        shared = resp.json()["data"]["comparison"]["shared_technologies"]
        assert shared == [{"name": "React", "category": "frontend", "confidence_a": 90, "confidence_b": 70}]

    def test_compare_unknown_id_is_not_found(self, client):
        a = make_analysis()
        resp = client.get(f"/api/v1/analyses/compare/?a={a.pk}&b=999999")
        assert resp.status_code == 404

    def test_missing_param(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=1")
        assert resp.status_code == 400

    def test_equal_params(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=3&b=3")
        assert resp.status_code == 400


class TestCompareByUrl:
    def test_uses_existing_analyses(self, client):
        make_analysis(url="https://a.com", techs=[FAKE_TECHS[0]])
        make_analysis(url="https://b.com", techs=[FAKE_TECHS[1]])
        before = Analysis.objects.count()
        resp = client.post("/api/v1/analyses/compare/", {"url_a": "a.com", "url_b": "b.com"}, format="json")
        assert resp.status_code == 200
        assert Analysis.objects.count() == before  # no re-analizó, reusó los existentes
        comp = resp.json()["data"]["comparison"]
        assert [t["name"] for t in comp["only_in_a"]] == ["React"]
        assert [t["name"] for t in comp["only_in_b"]] == ["Nginx"]

    def test_analyzes_when_missing(self, client):
        resp = client.post("/api/v1/analyses/compare/", {"url_a": "new-a.com", "url_b": "new-b.com"}, format="json")
        assert resp.status_code == 200
        assert Analysis.objects.filter(domain__name="new-a.com").exists()
        assert Analysis.objects.filter(domain__name="new-b.com").exists()

    def test_compare_analysis_excludes_wayback(self, client):
        # Compare analiza en vivo SIN Wayback: ni WaybackResult ni error de wayback.
        client.post("/api/v1/analyses/compare/", {"url_a": "na.com", "url_b": "nb.com"}, format="json")
        a = Analysis.objects.get(domain__name="na.com")
        assert not WaybackResult.objects.filter(analysis=a).exists()
        assert not a.errors.filter(service="wayback").exists()

    def test_same_url_is_validation_error(self, client):
        resp = client.post("/api/v1/analyses/compare/", {"url_a": "a.com", "url_b": "a.com"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR


class TestStats:
    def test_stats_empty(self, client):
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_analyses"] == 0
        assert data["unique_domains"] == 0
        assert data["total_detections"] == 0
        assert data["avg_analysis_time_seconds"] is None
        assert data["avg_confidence"] is None
        assert data["top_technologies"] == []
        assert data["activity"] == []

    def test_stats_aggregates(self, client):
        make_analysis(url="https://a.com", techs=[FAKE_TECHS[0]])
        make_analysis(url="https://b.com", techs=FAKE_TECHS)
        resp = client.get("/api/v1/stats/")
        data = resp.json()["data"]
        assert data["total_analyses"] == 2
        assert data["unique_domains"] == 2
        assert data["total_detections"] == 3
        counts = {t["name"]: t["count"] for t in data["top_technologies"]}
        assert counts["React"] == 2
        assert counts["Nginx"] == 1
        assert data["by_category"]["frontend"] == 2
        assert data["by_category"]["server"] == 1
        assert data["avg_confidence"] is not None
