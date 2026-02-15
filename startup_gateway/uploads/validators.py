from rest_framework.exceptions import ValidationError

IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp",  "image/svg+xml"]
DOC_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOC_SIZE = 10 * 1024 * 1024


def validate_upload(file, purpose=None):
    purpose = (purpose or "").strip().lower()

    if purpose in {"logo", "image"}:
        if file.content_type not in IMAGE_TYPES:
            raise ValidationError("Invalid file type")
        if file.size > MAX_IMAGE_SIZE:
            raise ValidationError("Image too large")
        return "image"

    if purpose in {"pitch_deck", "deck", "doc", "document"}:
        if file.content_type not in DOC_TYPES:
            raise ValidationError("Invalid file type")
        if file.size > MAX_DOC_SIZE:
            raise ValidationError("Document too large")
        return "doc"

    if file.content_type in IMAGE_TYPES:
        if file.size > MAX_IMAGE_SIZE:
            raise ValidationError("Image too large")
        return "image"

    if file.content_type in DOC_TYPES:
        if file.size > MAX_DOC_SIZE:
            raise ValidationError("Document too large")
        return "doc"

    raise ValidationError("Invalid file type")