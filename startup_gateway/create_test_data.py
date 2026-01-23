# create_test_data.py
import os
import sys
import django

# Додати шлях до проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Налаштувати Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'startup_gateway.settings')
django.setup()

from django.contrib.auth import get_user_model
from startups.models import StartupProfile
from projects.models import Project, ProjectStatus, ProjectVisibility

def create_test_data():
    User = get_user_model()
    
    print("Creating test data...")
    
    # Створити або отримати користувача
    user, created = User.objects.get_or_create(
        email='test@startup.com',
        defaults={
            'username': 'testowner',
            'password': 'test123',
            'first_name': 'Test',
            'last_name': 'Startup'
        }
    )
    if created:
        user.set_password('test123')
        user.save()
        print("✅ User created")
    else:
        print("✅ User already exists")
    
    # Створити або отримати стартап
    startup, created = StartupProfile.objects.get_or_create(
        user=user,
        defaults={
            'company_name': 'Tech Innovations Inc.',
            'short_pitch': 'We create amazing products',
            'website': 'https://example.com'
        }
    )
    
    if created:
        print(f"✅ Startup created with ID: {startup.id}")
    else:
        print(f"✅ Startup exists with ID: {startup.id}")
    
    # Перевірити чи є вже проекти
    existing_projects = startup.projects.count()
    if existing_projects == 0:
        # Створити 6 тестових проектів (для пагінації)
        projects_data = [
            {
                'title': 'AI Assistant',
                'short_desc': 'Intelligent AI assistant',
                'status': ProjectStatus.ACTIVE,
                'target': 50000
            },
            {
                'title': 'Eco Packaging',
                'short_desc': 'Sustainable packaging',
                'status': ProjectStatus.ACTIVE,
                'target': 30000
            },
            {
                'title': 'Mobile App',
                'short_desc': 'Cross-platform mobile app',
                'status': ProjectStatus.FUNDED,
                'target': 25000
            },
            {
                'title': 'IoT Device',
                'short_desc': 'Smart home device',
                'status': ProjectStatus.PROTOTYPE,
                'target': 40000
            },
            {
                'title': 'Web Platform',
                'short_desc': 'SaaS web platform',
                'status': ProjectStatus.ACTIVE,
                'target': 35000
            },
            {
                'title': 'Blockchain Solution',
                'short_desc': 'Decentralized application',
                'status': ProjectStatus.IDEA,
                'target': 60000
            },
        ]
        
        for i, data in enumerate(projects_data, 1):
            Project.objects.create(
                startup_profile=startup,
                title=data['title'],
                slug=f"{data['title'].lower().replace(' ', '-')}-{i}",
                short_description=data['short_desc'],
                description=f"Full description of {data['title']} project...",
                status=data['status'],
                target_amount=data['target'],
                visibility=ProjectVisibility.PUBLIC
            )
        print(f"✅ Created {len(projects_data)} test projects")
    else:
        print(f"✅ Already have {existing_projects} projects")
    
    print(f"\n🎯 Test URLs:")
    print(f"   GET http://localhost:8000/api/startups/{startup.id}/projects/")
    print(f"   GET http://localhost:8000/api/startups/{startup.id}/projects/?page_size=3")
    print(f"   GET http://localhost:8000/api/startups/{startup.id}/projects/?status=active")
    
    return startup.id

if __name__ == '__main__':
    startup_id = create_test_data()