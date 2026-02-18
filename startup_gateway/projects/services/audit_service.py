from decimal import Decimal

AUDITABLE_FIELDS = [
    "title",
    "slug",
    "short_description",
    "description",
    "thumbnail_url",
    "status",
    "target_amount",
    "currency",
    "allow_overfunding",
    "visibility",
]

def serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


def build_diff(instance, validated_data):
    diff = {}

    for field in AUDITABLE_FIELDS:
        if field not in validated_data:
            continue

        old_value = getattr(instance, field)
        new_value = validated_data[field]

        if old_value != new_value:
            diff[field] = {
                "before": serialize_value(old_value),
                "after": serialize_value(new_value),
            }

    return diff
