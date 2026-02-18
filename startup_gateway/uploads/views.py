from django.shortcuts import render
from rest_framework.response import Response
from .models import Upload
from .serializers import UploadSerializer
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError 
from .validators import validate_upload


class UploadCreateAPIView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        purpose = request.data.get("purpose")

        if not file:
            return Response(
                {"file": "This field is required."},
                status=400
            )

        try:
            upload_type = validate_upload(file, purpose=purpose)
        except ValidationError as e:
            detail = getattr(e, "detail", None)
            if isinstance(detail, (list, tuple)) and detail:
                msg = str(detail[0])
            elif detail is not None:
                msg = str(detail)
            else:
                msg = str(e)

            return Response({"file": msg}, status=400)

        upload = Upload.objects.create(
            user=request.user, 
            file=file,
            type=upload_type,
            size=file.size,
            content_type=file.content_type,
        )

        return Response(UploadSerializer(upload, context={"request": request}).data, status=201)