from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from startups.models import StartupProfile
from dashboard.models import SavedStartup
from investors.models import InvestorProfile

User = get_user_model()


class StartupApiTests(APITestCase):

    def setUp(self):
        self.startup_user = User.objects.create_user(
            username='teststartup',
            email='startup@test.com',
            password='123456'
        )

        self.investor_user = User.objects.create_user(
            username='investor',
            email='investor@test.com',
            password='123456'
        )

        self.startup = StartupProfile.objects.create(
            user=self.startup_user,
            company_name='Test Startup',
            slug='test-startup',
        )


    def test_get_startup_public_profile(self):
        response = self.client.get('/api/startups/test-startup/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['company_name'], 'Test Startup')
        self.assertIn('followers_count', response.data)
        self.assertIn('projects_count', response.data)
        self.assertIn('tags', response.data)


    def test_get_startup_profile_404(self):
        response = self.client.get('/api/startups/non-existent-slug/')
        self.assertEqual(response.status_code, 404)


    def test_followers_count_zero(self):
        response = self.client.get('/api/startups/test-startup/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['followers_count'], 0)


    def test_followers_count_when_saved(self):
        investor_profile = InvestorProfile.objects.create(
            user=self.investor_user,
            company_name="Test Investor Corp"
        )
        SavedStartup.objects.create(
            startup_profile=self.startup,
            investor_profile=investor_profile
        )
        response = self.client.get('/api/startups/test-startup/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['followers_count'], 1)
