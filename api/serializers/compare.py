from rest_framework import serializers


class CompareQuerySerializer(serializers.Serializer):
    a = serializers.IntegerField(min_value=1)
    b = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["a"] == attrs["b"]:
            raise serializers.ValidationError(
                "Parameters 'a' and 'b' must reference different analyses."
            )
        return attrs
