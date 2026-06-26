from rest_framework.response import Response


def success_response(data=None, meta=None, status_code=200):
    return Response(
        {
            "success": True,
            "data": data,
            "error": None,
            "meta": meta or {},
        },
        status=status_code,
    )


def error_response(code, message, status_code, meta=None):
    return Response(
        {
            "success": False,
            "data": None,
            "error": {"code": code, "message": message},
            "meta": meta or {},
        },
        status=status_code,
    )
