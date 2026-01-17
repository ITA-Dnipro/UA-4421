# users/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from startups.models import StartupProfile
from investors.models import InvestorProfile
from projects.models import Project
from dashboard.models import SavedStartap
from messages.models import Message
from notifications.models import Notification
from users.models import Role, UserRole


User = get_user_model()

class TestModels(TestCase):
    fixtures = ['users/fixtures/initial_data.json']

    def test_user_fields(self):
        startup_user = User.objects.get(username='startup_user')
        investor_user = User.objects.get(username='investor_user')
        self.assertEqual(startup_user.first_name, 'Anna')
        self.assertEqual(investor_user.first_name, 'Ivan')

    def test_roles(self):
        role_startup = Role.objects.get(name='startup')
        role_investor = Role.objects.get(name='investor')
        self.assertEqual(role_startup.users.count(), 1)
        self.assertEqual(role_investor.users.count(), 1)

    def test_userroles(self):
        startup_user = User.objects.get(username='startup_user')
        investor_user = User.objects.get(username='investor_user')
        self.assertTrue(UserRole.objects.filter(user=startup_user, role__name='startup').exists())
        self.assertTrue(UserRole.objects.filter(user=investor_user, role__name='investor').exists())

    def test_startupprofile(self):
        startup_profile = StartupProfile.objects.get(company_name='Example Startup')
        self.assertEqual(startup_profile.user.username, 'startup_user')

    def test_investorprofile(self):
        investor_profile = InvestorProfile.objects.get(company_name='Example Investor')
        self.assertEqual(investor_profile.user.username, 'investor_user')

    def test_project(self):
        project = Project.objects.get(title='Example Project')
        self.assertEqual(project.startup_profile.company_name, 'Example Startup')

    def test_savedstartap(self):
        saved = SavedStartap.objects.get(investor_profile__company_name='Example Investor')
        self.assertEqual(saved.startap_profile.company_name, 'Example Startup')

    def test_message_model(self):
        startup_user = User.objects.get(username='startup_user')
        investor_user = User.objects.get(username='investor_user')
        project = Project.objects.get(title='Example Project')
        message = Message.objects.create(sender=investor_user, receiver=startup_user, project=project, body='Hello')
        self.assertEqual(message.body, 'Hello')

    def test_notification_model(self):
        startup_user = User.objects.get(username='startup_user')
        notif = Notification.objects.create(user=startup_user, type='test', payload={"msg": "ok"})
        self.assertEqual(notif.user.username, 'startup_user')
        self.assertFalse(notif.is_read)
