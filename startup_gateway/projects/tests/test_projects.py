import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APIClient
from projects.models import Project, ProjectAudit, ProjectStatus
from startups.models import StartupProfile
from projects.serializers import ProjectStateSerializer, ModerationActionSerializer, ProjectAuditSerializer
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def loaded_projects(django_db_blocker):
    from django.core.management import call_command
    with django_db_blocker.unblock():
        call_command("loaddata", "projects.json")
    return Project.objects.all()

@pytest.fixture(autouse=True)
def mock_external_services():
    with patch("notifications.tasks.handle_project_event.delay") as mock_notify, \
         patch("projects.services.project_state_service.ProjectSearchService") as mock_search:
        yield mock_notify, mock_search

@pytest.fixture
def force_on_commit(db):
    with patch("django.db.transaction.on_commit", side_effect=lambda func: func()):
        yield

@pytest.mark.django_db
class TestProjectAPI:

    def test_list_projects_visibility(self, api_client, loaded_projects):

        url = reverse("projects:startup-projects", kwargs={"startup_id": loaded_projects.first().startup_profile.id})
        response = api_client.get(url)
        assert response.status_code == 200

        for p in response.data:
            assert Project.objects.get(id=p['id']).visibility == 'public'

    def test_create_project_with_audit_and_notification(self, api_client, loaded_projects, mock_external_services):
        mock_notify, _ = mock_external_services
        startup = loaded_projects.first().startup_profile
        api_client.force_authenticate(user=startup.user)
        
        url = reverse("projects:startup-projects", kwargs={"startup_id": startup.id})
        data = {
            "title": "Test Audit Project",
            "slug": "test-audit",
            "short_description": "desc",
            "description": "long desc",
            "status": "idea",
            "target_amount": "5000.00",
            "currency": "USD",
            "visibility": "public"
        }
        
        response = api_client.post(url, data, format="json")
        assert response.status_code == 201
        
        project_id = response.data['id']
        assert ProjectAudit.objects.filter(project_id=project_id, action='create').exists()
        
        assert mock_notify.called
        assert mock_notify.call_args[1]['event_type'] == "project_created"


    def test_upload_project_attachment(self, api_client, loaded_projects):
        project = loaded_projects.first()
        user = project.startup_profile.user
        api_client.force_authenticate(user=user)

        from uploads.models import Upload
        file_content = b"fake content"
        fake_file = SimpleUploadedFile("test.img", file_content, content_type="image")
        
        upload_obj = Upload.objects.create(
            user=user,
            file=fake_file,
            type="img",
            size=len(file_content),
            content_type="image"
        )

        url = reverse("projects:project-attachment-create")
        
        data = {
            "project": project.id,
            "upload": upload_obj.id, 
            "type": "thumbnail",     
            "caption": "image",
            "order": 1
        }

        response = api_client.post(url, data, format="json")
            
        assert response.status_code == 201
        assert project.attachments.count() == 1


    def test_invalid_status_transition(self, api_client, loaded_projects):
        project = loaded_projects.filter(status=ProjectStatus.IDEA).first()
        api_client.force_authenticate(user=project.startup_profile.user)
        
        url = reverse("projects:project-state-service", kwargs={"pk": project.id})
        response = api_client.patch(url, {"status": ProjectStatus.FUNDED}, format="json")
        
        assert response.status_code == 400
        assert "Transition" in response.data['detail']


    def test_search_sync_on_visibility_change(self, api_client, loaded_projects, mock_external_services, force_on_commit):
        _, mock_search_class = mock_external_services 

        mock_search_instance = mock_search_class.return_value 
        
        project = loaded_projects.first()
        api_client.force_authenticate(user=project.startup_profile.user)
        url = reverse("projects:project-state-service", kwargs={"pk": project.id})

        response = api_client.patch(url, {"visibility": "private"}, format="json")
        assert response.status_code == 200

        assert mock_search_instance.remove_project.called


    def test_project_history_endpoint(self, api_client, loaded_projects):
        project = loaded_projects.first()
        api_client.force_authenticate(user=project.startup_profile.user)
        
        url_patch = reverse("projects:project-rud", kwargs={"pk": project.id})
        api_client.patch(url_patch, {"title": "Updated Title"}, format="json")
        
        url_history = reverse("projects:project-history", kwargs={"pk": project.id})
        response = api_client.get(url_history)
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['action'] == 'update'

    def test_permission_denied_for_non_owner(self, api_client, loaded_projects):

        project = loaded_projects.first()
        other_startup = StartupProfile.objects.all()[1]
        api_client.force_authenticate(user=other_startup.user)
        
        url = reverse("projects:project-rud", kwargs={"pk": project.id})
        response = api_client.patch(url, {"title": "Hacked"}, format="json")
        
        assert response.status_code == 403

    def test_soft_delete_execution(self, api_client, loaded_projects):

        project = loaded_projects.first()
        api_client.force_authenticate(user=project.startup_profile.user)
        
        url = reverse("projects:project-rud", kwargs={"pk": project.id})
        response = api_client.delete(url)
        
        assert response.status_code == 204
        project.refresh_from_db()
        assert project.is_deleted is True
        assert ProjectAudit.objects.filter(project=project, action='delete').exists()

@pytest.mark.unit
class TestProjectSerializersUnit:

    def test_project_state_serializer_validation_fail(self):

        data = {} 
        serializer = ProjectStateSerializer(data=data)
        
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "At least one field" in str(excinfo.value)

    def test_project_state_serializer_success(self):

        data = {"status": "mvp"}
        serializer = ProjectStateSerializer(data=data)
        assert serializer.is_valid() is True


    def test_moderation_reject_requires_reason(self):

        data = {
            "action": "reject",
            "reason": "" 
        }
        serializer = ModerationActionSerializer(data=data)
        assert serializer.is_valid() is False
        assert "reason" in serializer.errors

    def test_moderation_approve_no_reason_needed(self):

        data = {
            "action": "approve",
            "notes": "Looks good"
        }
        serializer = ModerationActionSerializer(data=data)
        assert serializer.is_valid() is True


    def test_project_audit_serializer_read_only(self):

        data = {
            "action": "delete",
            "user": 999  
        }

        serializer = ProjectAuditSerializer(data=data)
        serializer.is_valid()
        assert "user" not in serializer.validated_data