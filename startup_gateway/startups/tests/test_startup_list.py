from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from startups.models import StartupProfile, Region
from projects.models import Project, Tag

User = get_user_model()


class StartupListAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            username='teststartup1',
            email="startup1@test.com",
            password="password123"
        )
        cls.user2 = User.objects.create_user(
            username='teststartup2',
            email="startup2@test.com",
            password="password123"
        )

        cls.region_lviv = Region.objects.create(name="Lviv")
        cls.region_kyiv = Region.objects.create(name="Kyiv")

        cls.startup1 = StartupProfile.objects.create(
            user=cls.user1,
            company_name="Handmade Co",
            short_pitch="Woodwork and ceramics",
            logo_url="https://placehold.co/300x300"
        )
        cls.startup1.region.add(cls.region_lviv)

        cls.startup2 = StartupProfile.objects.create(
            user=cls.user2,
            company_name="Tech Future",
            short_pitch="AI & Robotics",
            logo_url="https://placehold.co/300x300"
        )
        cls.startup2.region.add(cls.region_kyiv)

        cls.tag_craft = Tag.objects.create(name="craft")
        cls.tag_pottery = Tag.objects.create(name="pottery")
        cls.tag_ai = Tag.objects.create(name="ai")

        project1 = Project.objects.create(
            startup_profile=cls.startup1,
            title="Ceramics Platform",
            slug="ceramics",
            short_description="Clay and craft",
            description="Full description",
            target_amount=10000
        )
        project1.tags.add(cls.tag_craft, cls.tag_pottery)

        project2 = Project.objects.create(
            startup_profile=cls.startup2,
            title="AI Startup",
            slug="ai-startup",
            short_description="AI solutions",
            description="Full description",
            target_amount=50000
        )
        project2.tags.add(cls.tag_ai)


    def test_startup_list_returns_200(self):
        url = reverse("startup-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(len(response.data["results"]), 2)


    def test_response_structure(self):
        url = reverse("startup-list")
        response = self.client.get(url)

        startup = response.data["results"][0]

        expected_fields = {
            "id",
            "company_name",
            "short_description",
            "thumbnail_url",
            "regions",
            "tags",
        }

        self.assertTrue(expected_fields.issubset(startup.keys()))


    def test_filter_by_tag(self):
        url = reverse("startup-list")
        response = self.client.get(url, {"tag": "craft"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["company_name"],
            "Handmade Co"
        )

    def test_filter_by_non_existing_tag_returns_empty(self):
        url = reverse("startup-list")
        response = self.client.get(url, {"tag": "nonexistent"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)


    def test_search_by_company_name(self):
        url = reverse("startup-list")
        response = self.client.get(url, {"search": "Handmade"})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["company_name"],
            "Handmade Co"
        )


    def test_regions_are_correctly_serialized(self):
        url = reverse("startup-list")
        response = self.client.get(url)

        handmade = next(
            s for s in response.data["results"]
            if s["company_name"] == "Handmade Co"
        )

        self.assertIn("Lviv", handmade["regions"])


    def test_tags_are_aggregated_from_projects(self):
        url = reverse("startup-list")
        response = self.client.get(url)

        handmade = next(
            s for s in response.data["results"]
            if s["company_name"] == "Handmade Co"
        )

        self.assertCountEqual(
            handmade["tags"],
            ["craft", "pottery"]
        )


    def test_pagination_respects_page_size(self):
        url = reverse("startup-list")
        response = self.client.get(url, {"page_size": 1})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])