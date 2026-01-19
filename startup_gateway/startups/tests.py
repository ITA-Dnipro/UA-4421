from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from startups.models import StartupProfile

User = get_user_model()

class StartupApiTests(APITestCase):
    
    def test_get_startup_public_profile(self):
        user = User.objects.create_user(
            username='teststartup',
            email='startup@test.com',
            password='123456'
        )

        startup = StartupProfile.objects.create(
            user=user,
            company_name='Test Startup',
            slug='test-startup',
        )

        response = self.client.get(f'/api/startups/{startup.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['company_name'], 'Test Startup')
        
        self.assertIn('followers_count', response.data)
        self.assertIn('projects_count', response.data)
        self.assertIn('tags', response.data)

    def test_get_startup_profile_404(self):
        response = self.client.get('/api/startups/99999/')

        self.assertEqual(response.status_code, 404)