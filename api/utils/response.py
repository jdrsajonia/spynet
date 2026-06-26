from rest_framework.response import Response


def success_envelope(data=None, meta=None):
    return {"success": True, "data": data, "error": None, "meta": meta or {}}


def error_envelope(code, message, meta=None):
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": meta or {},
    }


def success_response(data=None, meta=None, status_code=200):
    return Response(success_envelope(data, meta), status=status_code)


def error_response(code, message, status_code, meta=None):
    return Response(error_envelope(code, message, meta), status=status_code)
