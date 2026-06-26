import requests

from api.utils import error_codes
from api.utils.exception_handler import ExternalServiceError, custom_exception_handler


def _code(response):
    return response.data["error"]["code"]


def test_timeout_maps_to_external_service_error():
    response = custom_exception_handler(requests.exceptions.Timeout(), {})
    assert response.status_code == 502
    assert _code(response) == error_codes.EXTERNAL_SERVICE_ERROR


def test_connection_error_maps_to_external_service_error():
    response = custom_exception_handler(requests.exceptions.ConnectionError(), {})
    assert response.status_code == 502
    assert _code(response) == error_codes.EXTERNAL_SERVICE_ERROR


def test_external_service_exception_maps_to_502():
    response = custom_exception_handler(ExternalServiceError(), {})
    assert response.status_code == 502
    assert _code(response) == error_codes.EXTERNAL_SERVICE_ERROR


def test_unhandled_exception_maps_to_internal_error():
    response = custom_exception_handler(RuntimeError("boom"), {})
    assert response.status_code == 500
    assert _code(response) == error_codes.INTERNAL_ERROR


def test_envelope_shape_on_error():
    response = custom_exception_handler(RuntimeError("boom"), {})
    assert set(response.data.keys()) == {"success", "data", "error", "meta"}
    assert response.data["success"] is False
    assert response.data["data"] is None
