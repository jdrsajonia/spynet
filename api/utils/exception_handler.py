import logging

import requests
from django.http import Http404, JsonResponse
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from api.utils import error_codes
from api.utils.response import error_envelope, error_response

logger = logging.getLogger("spynet.api")

_STATUS_CODE_MAP = {
    400: error_codes.VALIDATION_ERROR,
    404: error_codes.NOT_FOUND,
    405: error_codes.METHOD_NOT_ALLOWED,
    502: error_codes.EXTERNAL_SERVICE_ERROR,
}


class ExternalServiceError(APIException):
    status_code = 502
    default_detail = "An upstream service is unavailable. Please try again later."
    default_code = error_codes.EXTERNAL_SERVICE_ERROR


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        code = _code_for(exc, response.status_code)
        meta = {"fields": response.data} if isinstance(exc, ValidationError) else None
        return error_response(
            code=code,
            message=_message_from_data(response.data),
            status_code=response.status_code,
            meta=meta,
        )

    # DRF did not recognise the exception: classify what's left ourselves.
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return error_response(
            code=error_codes.EXTERNAL_SERVICE_ERROR,
            message="An upstream service is unavailable. Please try again later.",
            status_code=502,
        )

    logger.exception("Unhandled exception in API view", exc_info=exc)
    return error_response(
        code=error_codes.INTERNAL_ERROR,
        message="An unexpected error occurred.",
        status_code=500,
    )

# Django invokes these for routing-level 404s and unhandled 500s that never
# reach a DRF view. They only take effect when DEBUG is False
def handler404(request, exception=None):
    return JsonResponse(
        error_envelope(error_codes.NOT_FOUND, "The requested resource was not found."),
        status=404,
    )


def handler500(request):
    return JsonResponse(
        error_envelope(error_codes.INTERNAL_ERROR, "An unexpected error occurred."),
        status=500,
    )


def _code_for(exc, status_code):
    if isinstance(exc, ValidationError):
        return error_codes.VALIDATION_ERROR
    if isinstance(exc, (NotFound, Http404)):
        return error_codes.NOT_FOUND
    if isinstance(exc, MethodNotAllowed):
        return error_codes.METHOD_NOT_ALLOWED
    return _STATUS_CODE_MAP.get(status_code, error_codes.INTERNAL_ERROR)


def _message_from_data(data):
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        return _flatten(data["detail"])
    return _flatten(data)


def _flatten(detail):
    if isinstance(detail, dict):
        return " ".join(f"{key}: {_flatten(value)}" for key, value in detail.items())
    if isinstance(detail, (list, tuple)):
        return " ".join(_flatten(item) for item in detail)
    return str(detail)
