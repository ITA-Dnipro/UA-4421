from django.shortcuts import render
from rest_framework.generics import RetrieveAPIView
from .models import StartupProfile
from .serializers import StartupPublicSerializer

# Create your views here.
class StartupPublicDetailView(RetrieveAPIView):
    queryset = (
        StartupProfile.objects
        .prefetch_related('projects__tags')
    )
    serializer_class = StartupPublicSerializer
    lookup_field = 'slug'