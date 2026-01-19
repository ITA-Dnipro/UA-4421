from django.shortcuts import render
from rest_framework.generics import RetrieveAPIView
from .models import StartupProfile
from .serializers import StartupPublicSerializer

# Create your views here.
class StartupPublicDetailView(RetrieveAPIView):
    queryset = StartupProfile.objects.all()
    serializer_class = StartupPublicSerializer