from django.forms import ValidationError
from projects.models import AttachmentTypes

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
DECK_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DECK_SIZE = 20 * 1024 * 1024


def validate_upload(file, role):
    if role == AttachmentTypes.THUMBNAIL:
        if file.content_type not in IMAGE_TYPES:
            raise ValidationError("Thumbnail must be an image")
        if file.size > MAX_IMAGE_SIZE:
            raise ValidationError("Image too large")
    if role == AttachmentTypes.DECK:
        if file.content_type not in DECK_TYPES:
            raise ValidationError("Invalid deck format")
        if file.size > MAX_DECK_SIZE:
            raise ValidationError("Deck too large")
