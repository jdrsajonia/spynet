from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers

_url_validator = URLValidator(schemes=["http", "https"])


class AnalysisInputSerializer(serializers.Serializer):
    url = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_url(self, value):
        normalized = self._normalize_url(value)
        try:
            _url_validator(normalized)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid URL.")
        return normalized

    @staticmethod
    def _normalize_url(value):
        value = value.strip()
        if value.startswith("//"):
            return "https:" + value
        if not value.startswith(("http://", "https://")):
            return "https://" + value
        return value
