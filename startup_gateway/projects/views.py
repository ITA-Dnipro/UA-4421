from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from projects.models import Project
from projects.services.change_project_status import change_project_status
from projects.serializers import ProjectStatusUpdateSerializer


class ProjectStatusUpdateView(APIView):

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        serializer = ProjectStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            change_project_status(
                project,
                serializer.validated_data["status"],
                #admin_override=request.user.is_staff
            )
        except ValidationError as e:
            return Response(
                {"detail": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"status": project.status})
