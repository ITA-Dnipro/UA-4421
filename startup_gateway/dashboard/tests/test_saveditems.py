import uuid
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from users.models import Role, UserRole
from investors.models import InvestorProfile
from startups.models import StartupProfile, Region
from projects.models import Project, Tag
from dashboard.models import SavedItem

User = get_user_model()


class SavedItemAPITests(APITestCase):
    def setUp(self):
        self.role_startup, _ = Role.objects.get_or_create(name='startup')
        self.role_investor, _ = Role.objects.get_or_create(name='investor')


        self.inv_user = User.objects.create_user(username='inv', email='inv@example.com', password='pw')
        UserRole.objects.create(user=self.inv_user, role=self.role_investor)
        self.inv_profile = InvestorProfile.objects.create(user=self.inv_user, company_name='InvCo')

        self.startup_user = User.objects.create_user(username='founder', email='founder@example.com', password='pw')
        UserRole.objects.create(user=self.startup_user, role=self.role_startup)
        self.startup_profile = StartupProfile.objects.create(
            user=self.startup_user,
            company_name='Handmade Co',
            slug='handmade-co'
        )

        self.tag = Tag.objects.create(name='craft')
        self.region = Region.objects.create(name='Lviv')
        self.project = Project.objects.create(
            id=uuid.uuid4(),
            startup_profile=self.startup_profile,
            title='Chairs',
            slug='chairs',
            short_description='chairs',
            description='desc',
            target_amount=100
        )
        self.project.tags.add(self.tag)
        if hasattr(self.project, 'regions'):
            self.project.regions.add(self.region)
        else:
            try:
                self.project.region = self.region
                self.project.save()
            except Exception:
                pass

    def test_create_saved_startup(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        assert r.status_code == 201
        assert 'saved_id' in r.data
        assert SavedItem.objects.filter(id=r.data['saved_id']).exists()

    def test_duplicate_create_is_idempotent(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r1 = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        r2 = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        assert r1.status_code == 201
        assert r2.status_code == 200
        assert r1.data['saved_id'] == r2.data['saved_id']

    def test_create_saved_project(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r = self.client.post(url, {"target_type": "project", "target_id": str(self.project.id)}, format='json')
        assert r.status_code == 201
        assert SavedItem.objects.filter(id=r.data['saved_id']).exists()

    def test_create_saved_company(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r = self.client.post(url, {"target_type": "company", "target_id": str(self.startup_user.id)}, format='json')
        assert r.status_code == 201
        assert SavedItem.objects.filter(id=r.data['saved_id']).exists()

    def test_cannot_save_own(self):
        both = User.objects.create_user(username='both', email='both@example.com', password='pw')
        UserRole.objects.create(user=both, role=self.role_investor)
        UserRole.objects.create(user=both, role=self.role_startup)
        both_inv = InvestorProfile.objects.create(user=both, company_name='BothInv')
        both_startup = StartupProfile.objects.create(user=both, company_name='BothStartup', slug='both')

        url = f'/api/users/{both.id}/saved/'
        self.client.force_authenticate(both)
        r = self.client.post(url, {"target_type": "startup", "target_id": str(both_startup.id)}, format='json')
        assert r.status_code == 400

    def test_invalid_target_returns_400(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r = self.client.post(url, {"target_type": "startup", "target_id": "99999"}, format='json')
        assert r.status_code == 400

    def test_unauthenticated_returns_401(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        r = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        assert r.status_code == 401

    def test_forbidden_if_url_user_mismatch(self):
        url = f'/api/users/{self.startup_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        r = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        assert r.status_code == 403

    def test_delete_saved(self):
        url = f'/api/users/{self.inv_user.id}/saved/'
        self.client.force_authenticate(self.inv_user)
        create = self.client.post(url, {"target_type": "startup", "target_id": str(self.startup_profile.id)}, format='json')
        saved_id = create.data['saved_id']
        delete_url = f'/api/users/{self.inv_user.id}/saved/{saved_id}/'
        r = self.client.delete(delete_url)
        assert r.status_code == 204
        assert not SavedItem.objects.filter(id=saved_id).exists()