import pytest
from rest_framework.test import APIClient

from api.utils import error_codes

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


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
        assert body["data"] == {"message": "not implemented"}
        assert body["meta"] == {"analysis_id": 1}

    def test_error_envelope_shape(self, client):
        resp = client.post("/api/v1/analyses/", {}, format="json")
        assert resp.status_code == 400
        body = resp.json()
        assert_envelope(body)
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["code"] == error_codes.VALIDATION_ERROR


class TestAnalyses:
    def test_create_ok(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "https://example.com"}, format="json")
        assert resp.status_code == 201

    def test_url_normalized_without_scheme(self, client):
        resp = client.post("/api/v1/analyses/", {"url": "github.com"}, format="json")
        assert resp.status_code == 201

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
        resp = client.get("/api/v1/analyses/1/")
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"analysis_id": 1}

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
        resp = client.get("/api/v1/analyses/compare/?a=1&b=2")
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"a": 1, "b": 2}

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
    def test_stats_ok(self, client):
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
