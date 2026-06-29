import pytest
from rest_framework.test import APIClient

from api.models import Analysis, Domain, Technology
from api.persistence import persist_analysis
from api.utils import error_codes

pytestmark = pytest.mark.django_db


FAKE_TECHS = [
    {"name": "React", "category": "frontend", "confidence": 100, "evidence": "html"},
    {"name": "Nginx", "category": "server", "confidence": 60, "evidence": "header"},
]


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture(autouse=True)
def mock_analyzer(monkeypatch):
    """
    Reemplaza el Analyzer compartido por funciones deterministas para que los
    tests del API no salgan a la red. El motor de detección se prueba aparte
    en tests/detectors/.
    """
    def fake_analyze(url):
        return {
            "url": url,
            "technologies": FAKE_TECHS,
            "dns": {"A": ["1.2.3.4"], "MX": ["10 mail.example.com"]},
            "whois": None,
            "geo": None,
            "wayback": None,
        }

    def fake_snapshot(url):
        return {"snapshot_url": url, "technologies": FAKE_TECHS}

    monkeypatch.setattr("api.views._analyzer.analyze", fake_analyze)
    monkeypatch.setattr("api.views._analyzer.analyze_snapshot", fake_snapshot)


def make_analysis(url="https://example.com", techs=None):
    """Crea un Analysis persistido directamente (sin pasar por la red ni la vista)."""
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


class TestAnalyses:
    def test_create_persists_normalized_graph(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        assert resp.status_code == 201
        analysis_id = resp.json()["meta"]["analysis_id"]

        analysis = Analysis.objects.get(pk=analysis_id)
        assert Domain.objects.filter(name="example.com").exists()
        assert analysis.technologies.count() == 2
        # whois/geo/wayback eran None -> deben quedar como AnalysisError; dns sí vino.
        assert analysis.status == "partial"
        assert set(analysis.errors.values_list("service", flat=True)) == {"whois", "geo", "wayback"}
        assert analysis.dns_result.records.count() == 2  # A + MX

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

    def test_get_not_allowed(self, client):
        resp = client.get("/api/v1/analyses/")
        assert resp.status_code == 405
        assert resp.json()["error"]["code"] == error_codes.METHOD_NOT_ALLOWED


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
        # Las tecnologías de snapshot cuelgan del WaybackSnapshot, no del Analysis.
        assert analysis.technologies.count() == 0
        snapshot = analysis.wayback_result.snapshots.get()
        assert snapshot.technologies.count() == 2

    def test_rejects_non_wayback_url(self, client):
        resp = client.post(
            "/api/v1/analyses/snapshot/", {"snapshot_url": "https://example.com"}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR

    def test_missing_snapshot_url(self, client):
        resp = client.post("/api/v1/analyses/snapshot/", {}, format="json")
        assert resp.status_code == 400


class TestDetail:
    def test_retrieve_ok(self, client):
        analysis = make_analysis()
        resp = client.get(f"/api/v1/analyses/{analysis.pk}/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"] == {"analysis_id": analysis.pk}
        assert body["data"]["id"] == analysis.pk
        names = {t["name"] for t in body["data"]["technologies"]}
        assert names == {"React", "Nginx"}

    def test_unknown_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/999999/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND

    def test_non_integer_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/abc/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND

    def test_zero_id_is_not_found(self, client):
        resp = client.get("/api/v1/analyses/0/")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND


class TestCompare:
    def test_compare_ok(self, client):
        a = make_analysis(url="https://a.com", techs=[FAKE_TECHS[0]])
        b = make_analysis(url="https://b.com", techs=[FAKE_TECHS[1]])
        resp = client.get(f"/api/v1/analyses/compare/?a={a.pk}&b={b.pk}")
        assert resp.status_code == 200
        comparison = resp.json()["data"]["comparison"]
        assert comparison["only_in_a"] == ["React"]
        assert comparison["only_in_b"] == ["Nginx"]
        assert comparison["shared_technologies"] == []

    def test_compare_unknown_id_is_not_found(self, client):
        a = make_analysis()
        resp = client.get(f"/api/v1/analyses/compare/?a={a.pk}&b=999999")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == error_codes.NOT_FOUND

    def test_missing_param(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=1")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR

    def test_non_integer_param(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=1&b=foo")
        assert resp.status_code == 400

    def test_equal_params(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=3&b=3")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == error_codes.VALIDATION_ERROR

    def test_non_positive_param(self, client):
        resp = client.get("/api/v1/analyses/compare/?a=0&b=1")
        assert resp.status_code == 400


class TestStats:
    def test_stats_empty(self, client):
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_analyses"] == 0
        assert data["top_technologies"] == []

    def test_stats_aggregates(self, client):
        make_analysis(techs=[FAKE_TECHS[0]])
        make_analysis(techs=FAKE_TECHS)
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_analyses"] == 2
        counts = {t["name"]: t["count"] for t in data["top_technologies"]}
        assert counts["React"] == 2
        assert counts["Nginx"] == 1
        assert data["by_category"]["frontend"] == 2
        assert data["by_category"]["server"] == 1
