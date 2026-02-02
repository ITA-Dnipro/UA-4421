from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from startups.models import StartupProfile
from projects.models import Project, Tag, ProjectStatus, ProjectVisibility

User = get_user_model()

class StartupProjectsAPITestCase(APITestCase):
    """Tests for startup projects API"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='startupowner',  # REQUIRED FIELD
            email='startup@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            phone='+380991234567',
            verified=True
        )
        
        # Create startup profile
        self.startup_profile = StartupProfile.objects.create(
            user=self.user,
            company_name='Tech Innovations Inc.',
            short_pitch='We create innovative tech solutions',
            website='https://techinnovations.com',
            slug='tech-innovations-inc'
        )
        
        # Create tags
        self.tech_tag = Tag.objects.create(name='Technology')
        self.eco_tag = Tag.objects.create(name='Eco-friendly')
        
        # Create test projects
        self.project1 = Project.objects.create(
            startup_profile=self.startup_profile,
            title='AI Assistant',
            slug='ai-assistant',
            short_description='An intelligent AI assistant that helps with daily tasks.',
            description='Full description of AI Assistant project...',
            thumbnail_url='https://example.com/ai-assistant.jpg',
            status=ProjectStatus.ACTIVE,
            target_amount=50000,
            raised_amount=25000,
            visibility=ProjectVisibility.PUBLIC
        )
        self.project1.tags.add(self.tech_tag)
        
        self.project2 = Project.objects.create(
            startup_profile=self.startup_profile,
            title='Eco Packaging',
            slug='eco-packaging',
            short_description='Sustainable packaging solution.',
            description='Full description of Eco Packaging...',
            thumbnail_url='',
            status=ProjectStatus.ACTIVE,
            target_amount=30000,
            raised_amount=15000,
            visibility=ProjectVisibility.PUBLIC
        )
        self.project2.tags.add(self.eco_tag)
        
        self.project3 = Project.objects.create(
            startup_profile=self.startup_profile,
            title='Private Project',
            slug='private-project',
            short_description='Not visible to public.',
            description='Private project description...',
            thumbnail_url='https://example.com/private.jpg',
            status=ProjectStatus.IDEA,
            target_amount=10000,
            raised_amount=0,
            visibility=ProjectVisibility.PRIVATE
        )
    
    def test_get_startup_projects_success(self):
        """Test successful retrieval of startup projects"""
        url = reverse('startups_api:startup-projects', args=[self.startup_profile.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)
        
        # By default, we only show PUBLIC projects
        self.assertEqual(data['count'], 2)  # Only 2 public projects
        
        # Check fields
        first_project = data['results'][0]
        expected_fields = ['id', 'title', 'status', 'thumbnail', 'short_desc']
        
        for field in expected_fields:
            self.assertIn(field, first_project)
    
    def test_filter_by_status(self):
        """Test filtering projects by status"""
        url = reverse('startups_api:startup-projects', args=[self.startup_profile.id])
        
        # Filter only active projects
        response = self.client.get(f'{url}?status={ProjectStatus.ACTIVE}')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['count'], 2)
        
        for project in data['results']:
            self.assertEqual(project['status'], ProjectStatus.ACTIVE)
    
    def test_filter_by_tag(self):
        """Test filtering projects by tag"""
        url = reverse('startups_api:startup-projects', args=[self.startup_profile.id])
        
        # Filter by 'Technology' tag
        response = self.client.get(f'{url}?tag=Technology')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['count'], 1)
        
        self.assertEqual(data['results'][0]['title'], 'AI Assistant')
    
    def test_pagination(self):
        """Test pagination according to specification"""
        # Add more projects
        for i in range(10):
            Project.objects.create(
                startup_profile=self.startup_profile,
                title=f'Extra Project {i}',
                slug=f'extra-project-{i}',
                short_description=f'Description {i}',
                status=ProjectStatus.ACTIVE,
                target_amount=1000 * i,
                visibility=ProjectVisibility.PUBLIC
            )
        
        url = reverse('startups_api:startup-projects', args=[self.startup_profile.id])
        
        # Default pagination (page_size=6)
        response = self.client.get(url)
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['results']), 6)
        
        # Custom pagination
        response = self.client.get(f'{url}?page=2&page_size=4')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['results']), 4)