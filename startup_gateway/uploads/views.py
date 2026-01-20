from django.shortcuts import render, Response
from .models import Upload
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView


class UploadCreateView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES["file"]
        upload = Upload.objects.create(
            file=file,
            mime_type=file.content_type,
            size=file.size,
        )
        return Response({
            "id": upload.id,
            "url": upload.file.url,
            "mime_type": upload.mime_type,
            "size": upload.size,
        }, status=201)

