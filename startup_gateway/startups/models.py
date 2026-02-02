from django.db import models
from django.conf import settings
from django.utils.text import slugify


User = settings.AUTH_USER_MODEL

class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return self.name

class StartupProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='startup_profile'
    )
    company_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    short_pitch = models.TextField(blank=True)
    about_html = models.TextField(blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    logo_url = models.URLField(blank=True)
    hero_image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    region = models.ManyToManyField(
        Region,
        related_name='startups',
        blank=True
    )

    class Meta:
        db_table = 'startup_profiles'
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.company_name)
            slug = base_slug
            counter = 1

            while StartupProfile.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name