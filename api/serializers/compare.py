from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers

_url_validator = URLValidator(schemes=["http", "https"])


def _normalize_url(value):
    value = value.strip()
    if value.startswith("//"):
        return "https:" + value
    if not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


class CompareQuerySerializer(serializers.Serializer):
    """Compara dos análisis YA guardados, por id (GET ?a=&b=)."""
    a = serializers.IntegerField(min_value=1)
    b = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["a"] == attrs["b"]:
            raise serializers.ValidationError(
                "Parameters 'a' and 'b' must reference different analyses."
            )
        return attrs


class CompareUrlSerializer(serializers.Serializer):
    """
    Compara dos sitios por URL (POST). Cada URL se resuelve al último análisis
    guardado de su dominio, o se analiza si no existe (opción B).
    """
    url_a = serializers.CharField(allow_blank=False, trim_whitespace=True)
    url_b = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_url_a(self, value):
        return self._validate_url(value)

    def validate_url_b(self, value):
        return self._validate_url(value)

    def validate(self, attrs):
        if attrs["url_a"] == attrs["url_b"]:
            raise serializers.ValidationError("url_a and url_b must be different.")
        return attrs

    @staticmethod
    def _validate_url(value):
        normalized = _normalize_url(value)
        try:
            _url_validator(normalized)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid URL.")
        return normalized
