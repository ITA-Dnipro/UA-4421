from dashboard.models import SavedStartup
from django.contrib.auth import get_user_model
from django.test import TestCase
from investors.models import InvestorProfile
from messages.models import Message
from notifications.models import Notification
from projects.models import (AttachmentType, Project, ProjectAttachment,
                             ProjectAudit, ProjectStatus, ProjectVisibility,
                             Tag)
from startups.models import StartupProfile
from users.models import Role, UserRole

User = get_user_model()


class TestModels(TestCase):
    fixtures = ["initial_data.json"]

    @classmethod
    def setUpTestData(cls):
        cls.startup_user = User.objects.get(username="startup_user")
        cls.investor_user = User.objects.get(username="investor_user")

        cls.startup_profile = StartupProfile.objects.get(user=cls.startup_user)
        cls.investor_profile = InvestorProfile.objects.get(user=cls.investor_user)

        cls.project = Project.objects.get(title="Example Project")

    def test_user_fields(self):
        self.assertEqual(self.startup_user.first_name, "Anna")
        self.assertEqual(self.investor_user.first_name, "Ivan")

    def test_roles(self):
        role_startup = Role.objects.get(name="startup")
        role_investor = Role.objects.get(name="investor")
        self.assertEqual(role_startup.users.count(), 1)
        self.assertEqual(role_investor.users.count(), 1)

    def test_userroles(self):
        self.assertTrue(
            UserRole.objects.filter(
                user=self.startup_user, role__name="startup"
            ).exists()
        )
        self.assertTrue(
            UserRole.objects.filter(
                user=self.investor_user, role__name="investor"
            ).exists()
        )

    def test_startupprofile(self):
        startup_profile = StartupProfile.objects.get(company_name="Example Startup")
        self.assertEqual(startup_profile.user.username, "startup_user")

    def test_investorprofile(self):
        investor_profile = InvestorProfile.objects.get(company_name="Example Investor")
        self.assertEqual(investor_profile.user.username, "investor_user")

    def test_project_existing(self):
        project = Project.objects.get(title="Example Project")
        self.assertEqual(project.startup_profile.company_name, "Example Startup")

    def test_savedstartup(self):
        saved = SavedStartup.objects.get(
            investor_profile__company_name="Example Investor"
        )
        self.assertEqual(saved.startup_profile.company_name, "Example Startup")

    def test_message_model(self):
        project = Project.objects.get(title="Example Project")
        message = Message.objects.create(
            sender=self.investor_user,
            receiver=self.startup_user,
            project=project,
            body="Hello",
        )
        self.assertEqual(message.body, "Hello")

    def test_notification_model(self):
        notif = Notification.objects.create(
            user=self.startup_user, type="test", payload={"msg": "ok"}
        )
        self.assertEqual(notif.user.username, "startup_user")
        self.assertFalse(notif.is_read)

    def test_create_project_minimal(self):
        project = Project.objects.create(
            startup_profile=self.startup_profile,
            title="Test Project",
            slug="test-project",
            short_description="Short desc",
            description="Full description",
            target_amount=1000,
        )
        self.assertEqual(project.status, ProjectStatus.IDEA)
        self.assertEqual(project.visibility, ProjectVisibility.PUBLIC)
        self.assertEqual(project.raised_amount, 0)
        self.assertEqual(str(project), "Test Project")
        self.assertEqual(project.tags.count(), 0)

    def test_project_with_tags(self):
        project = Project.objects.create(
            startup_profile=self.startup_profile,
            title="Tagged Project",
            slug="tagged-project",
            short_description="Short desc",
            description="Full description",
            target_amount=2000,
        )
        tag1 = Tag.objects.create(name="AI")
        tag2 = Tag.objects.create(name="FinTech")
        project.tags.add(tag1, tag2)
        self.assertEqual(project.tags.count(), 2)

    def test_create_attachment(self):
        project = Project.objects.create(
            startup_profile=self.startup_profile,
            title="Project With Attachment",
            slug="proj-attach",
            short_description="Desc",
            description="Full",
            target_amount=1500,
        )
        att1 = ProjectAttachment.objects.create(
            project=project,
            type=AttachmentType.THUMBNAIL,
            order=1,
            caption="First image",
        )
        att2 = ProjectAttachment.objects.create(
            project=project, type=AttachmentType.DECK, order=0
        )
        attachments = project.attachments.all()
        self.assertEqual(attachments.count(), 2)
        self.assertEqual(list(attachments), [att2, att1])

    def test_create_audit(self):
        project = Project.objects.create(
            startup_profile=self.startup_profile,
            title="Audited Project",
            slug="audited-project",
            short_description="Desc",
            description="Full",
            target_amount=1000,
        )
        changes = {"title": ["Old Title", "New Title"]}
        audit = ProjectAudit.objects.create(
            project=project, user=self.startup_user, changes=changes
        )
        self.assertEqual(audit.project, project)
        self.assertEqual(audit.user, self.startup_user)
        self.assertEqual(audit.changes, changes)
        self.assertIsNotNone(audit.timestamp)
