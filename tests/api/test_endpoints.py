import pytest
from rest_framework.test import APIClient

from api.models import Analysis
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
    tests del API no salgan a la red (antes tardaban ~30s y eran flaky).
    El motor de detección se prueba aparte en tests/detectors/.
    """
    def fake_analyze(url):
        return {
            "url": url,
            "technologies": FAKE_TECHS,
            "dns": {"A": ["1.2.3.4"]},
            "whois": None,
            "geo": None,
            "wayback": None,
        }

    def fake_snapshot(url):
        return {"snapshot_url": url, "technologies": FAKE_TECHS}

    monkeypatch.setattr("api.views._analyzer.analyze", fake_analyze)
    monkeypatch.setattr("api.views._analyzer.analyze_snapshot", fake_snapshot)


def make_analysis(url="https://example.com", techs=None):
    return Analysis.objects.create(url=url, technologies=techs if techs is not None else FAKE_TECHS)


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
    def test_create_persists_and_returns_id(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        assert resp.status_code == 201
        analysis_id = resp.json()["meta"]["analysis_id"]
        assert Analysis.objects.filter(pk=analysis_id).exists()

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
    def test_create_ok(self, client):
        url = "https://web.archive.org/web/20200101000000/https://example.com"
        resp = client.post("/api/v1/analyses/snapshot/", {"snapshot_url": url}, format="json")
        assert resp.status_code == 201
        assert resp.json()["data"]["snapshot_url"] == url

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
        assert body["data"]["technologies"] == FAKE_TECHS

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
        data = resp.json()["data"]
        assert data["a"]["id"] == a.pk
        assert data["b"]["id"] == b.pk
        assert data["comparison"]["only_in_a"] == ["React"]
        assert data["comparison"]["only_in_b"] == ["Nginx"]
        assert data["comparison"]["shared_technologies"] == []

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
