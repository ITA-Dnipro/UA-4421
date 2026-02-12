from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from dashboard.models import SavedItem
from django.contrib.contenttypes.models import ContentType
from dashboard.serializers import SavedItemCreateSerializer, SavedItemListSerializer
from dashboard.pagination import SavedItemPagination
from startups.models import StartupProfile
from projects.models import Project
from users.models import User


class SavedItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id != int(user_id):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SavedItemCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        saved, created = SavedItem.objects.get_or_create(
            investor_profile=serializer.validated_data["investor"],
            content_type=serializer.validated_data["content_type"],
            object_id=serializer.validated_data["object_id"],
        )

        return Response(
            {
                "saved_id": saved.id,
                "saved_at": saved.created_at.isoformat().replace('+00:00', 'Z'),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, user_id, saved_id):
        if request.user.id != int(user_id):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        saved = get_object_or_404(SavedItem, id=saved_id, investor_profile__user=request.user)
        saved.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

    def get(self, request, user_id):
        if request.user.id != int(user_id):
            return Response({"detail": "Forbidden."}, status=403)

        investor = getattr(request.user, "investor_profile", None)
        if not investor:
            return Response(
                {"detail": "Investor profile not found."},
                status=400,
            )

        qs = (
            SavedItem.objects
            .filter(investor_profile=investor)
            .select_related("content_type")
            .order_by("-created_at")
        )


        type_param = request.query_params.get("type")
        if type_param:
            ct_map = {
                "project": ContentType.objects.get(
                    app_label="projects", model="project"
                ),
                "startup": ContentType.objects.get(
                    app_label="startups", model="startupprofile"
                ),
                "company": ContentType.objects.get(
                    app_label="users", model="user"
                ),
            }
            content_type = ct_map.get(type_param)
            if content_type:
                qs = qs.filter(content_type=content_type)

        paginator = SavedItemPagination()
        page = paginator.paginate_queryset(qs, request)
        saved_items = list(page)


        project_ids = []
        startup_ids = []
        company_ids = []

        for item in saved_items:
            model = item.content_type.model

            if model == "project":
                project_ids.append(item.object_id)
            elif model == "startupprofile":
                startup_ids.append(item.object_id)
            elif model == "user":
                company_ids.append(item.object_id)


        projects = {
            p.id: p
            for p in Project.objects
            .filter(id__in=project_ids)
            .prefetch_related("tags")
        }

        startups = {
            s.uuid: s
            for s in StartupProfile.objects
            .filter(uuid__in=startup_ids)
            .prefetch_related("projects__tags", "region")
        }

        companies = {
            u.uuid: u
            for u in User.objects
            .filter(uuid__in=company_ids)
            .select_related("startup_profile")
            .prefetch_related("startup_profile__projects__tags")
        }

        results = []

        for item in saved_items:
            model = item.content_type.model
            obj_id = item.object_id

            target = None
            item_type = None

            if model == "project":
                target = projects.get(obj_id)
                item_type = "project"

            elif model == "startupprofile":
                target = startups.get(obj_id)
                item_type = "startup"

            elif model == "user":
                target = companies.get(obj_id)
                item_type = "company"

            if not target:
                continue

            if item_type == "project":
                tags = list(
                    target.tags.values_list("name", flat=True)
                )

            elif item_type == "startup":
                tags = list(
                    target.projects
                    .values_list("tags__name", flat=True)
                    .distinct()
                )

            elif item_type == "company":
                try:
                    sp = target.startup_profile
                except StartupProfile.DoesNotExist:
                    sp = None

                if sp:
                    tags = list(
                        sp.projects
                        .values_list("tags__name", flat=True)
                        .distinct()
                    )
                else:
                    tags = []
            else:
                tags = []

            location = ""
            if hasattr(target, "region"):
                regions = target.region.all()
                location = ", ".join(r.name for r in regions)

            results.append({
                "id": obj_id,
                "saved_id": item.id,
                "type": item_type,
                "title": getattr(target, "title", "") or getattr(target, "company_name", ""),
                "slug": getattr(target, "slug", ""),
                "thumbnail_url": getattr(target, "thumbnail_url", "") or getattr(target, "logo_url", ""),
                "short_description": getattr(target, "short_description", "") or getattr(target, "short_pitch", ""),
                "location": location,
                "tags": tags,
                "saved_at": item.created_at,
            })

        serializer = SavedItemListSerializer(results, many=True)
        return paginator.get_paginated_response(serializer.data)