from django.shortcuts import render
from rest_framework.response import Response
from .models import Upload
from .serializers import UploadSerializer
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .validators import validate_upload


class UploadCreateAPIView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "File not provided"},
                status=400
            )

        upload_type = validate_upload(file)

        upload = Upload.objects.create(
            file=file,
            type=upload_type,
            size=file.size,
            content_type=file.content_type,
        )

        return Response(UploadSerializer(upload).data, status=201)