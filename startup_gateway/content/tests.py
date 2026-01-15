from rest_framework.test import APITestCase

from .landing_content import LANDING_CONTENT
from .models import LandingContent


class TestLandingContentApi(APITestCase):
    def test_fallback_when_no_db_record(self):
        resp = self.client.get("/api/content/landing/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, LANDING_CONTENT)

    def test_returns_db_content_when_exists(self):
        LandingContent.objects.create(
            hero={"title": "DB title", "subtitle": "DB subtitle", "cta_text": "Join", "hero_images": []},
            for_whom=[],
            why_worth=[],
            footer_links={"left": [], "right": []},
        )

        resp = self.client.get("/api/content/landing/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["hero"]["title"], "DB title")
        self.assertIn("footer_links", resp.data)
