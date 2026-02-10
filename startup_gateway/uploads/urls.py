from django.urls import path
from .views import UploadCreateAPIView


urlpatterns = [
    path("", UploadCreateAPIView.as_view(), name="upload-create"),
]