"""
Helpers para el esquema OpenAPI.

Las vistas no devuelven el payload pelado: lo envuelven en
`{success, data, error, meta}` (ver `api.utils.response`). `envelope()` construye
el serializer de esa envoltura para un `data` dado, de modo que la documentación
describa lo que el cliente recibe de verdad, no solo el contenido de `data`.
"""
from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework import serializers

from api.serializers.responses import ErrorResponseSerializer


def envelope(name, data, meta=None):
    """Serializer de respuesta exitosa con `data` dentro de la envoltura estándar."""
    return inline_serializer(
        name=name,
        fields={
            "success": serializers.BooleanField(default=True),
            "data": data,
            "error": serializers.JSONField(allow_null=True, default=None),
            "meta": meta if meta is not None else serializers.DictField(),
        },
    )


def error(description):
    return OpenApiResponse(response=ErrorResponseSerializer, description=description)


# Errores que puede devolver cualquier vista. Se añaden explícitamente en cada
# `@extend_schema` porque OpenAPI no tiene herencia de respuestas.
VALIDATION = error("Entrada inválida (`VALIDATION_ERROR`). `meta.fields` detalla cada campo.")
NOT_FOUND = error("El recurso no existe (`NOT_FOUND`).")
RATE_LIMITED = error("Se superó el límite de peticiones por IP (`RATE_LIMITED`).")
UPSTREAM = error("Un servicio externo falló o expiró (`EXTERNAL_SERVICE_ERROR`).")
