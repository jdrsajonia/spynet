from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers

WAYBACK_PREFIX = "https://web.archive.org/"

_url_validator = URLValidator(schemes=["http", "https"])


class SnapshotInputSerializer(serializers.Serializer):
    snapshot_url = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_snapshot_url(self, value):
        value = value.strip()
        try:
            _url_validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid URL.")
        if not value.startswith(WAYBACK_PREFIX):
            raise serializers.ValidationError(
                f"snapshot_url must start with {WAYBACK_PREFIX}"
            )
        return value
