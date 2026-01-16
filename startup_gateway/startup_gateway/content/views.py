from django.db.utils import OperationalError, ProgrammingError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .landing_content import LANDING_CONTENT
from .models import LandingContent


@api_view(["GET"])
def landing_content(request):
    try:
        obj = LandingContent.objects.order_by("-updated_at").first()
    except (OperationalError, ProgrammingError):
        obj = None

    data = obj.as_dict() if obj else LANDING_CONTENT
    return Response(data)
