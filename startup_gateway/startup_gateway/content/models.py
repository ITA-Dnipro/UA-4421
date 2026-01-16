import copy
from django.db import models

from .landing_content import LANDING_CONTENT


def default_hero():
    return copy.deepcopy(LANDING_CONTENT["hero"])


def default_for_whom():
    return copy.deepcopy(LANDING_CONTENT["for_whom"])


def default_why_worth():
    return copy.deepcopy(LANDING_CONTENT["why_worth"])


def default_footer_links():
    return copy.deepcopy(LANDING_CONTENT["footer_links"])


class LandingContent(models.Model):
    hero = models.JSONField(default=default_hero)
    for_whom = models.JSONField(default=default_for_whom)
    why_worth = models.JSONField(default=default_why_worth)
    footer_links = models.JSONField(default=default_footer_links)
    updated_at = models.DateTimeField(auto_now=True)

    def as_dict(self):
        return {
            "hero": self.hero,
            "for_whom": self.for_whom,
            "why_worth": self.why_worth,
            "footer_links": self.footer_links,
        }

    def __str__(self):
        return f"LandingContent #{self.pk}"