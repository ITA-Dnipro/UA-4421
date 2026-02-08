import re
import uuid

from urllib.parse import urlparse
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db import IntegrityError
from django.utils.text import slugify

from rest_framework import serializers

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Role
from projects.models import Tag
from .services import register_user

User = get_user_model()


# =========================================================
# REGISTER
# =========================================================

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=())
    company_name = serializers.CharField(required=False, allow_blank=False)
    short_pitch = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        roles = [r.strip().lower() for r in Role.objects.values_list("name", flat=True)]
        self.fields["role"].choices = [(r, r) for r in roles]

    def validate(self, attrs):
        role = (attrs.get("role") or "").strip().lower()
        attrs["role"] = role
        company_name = attrs.get("company_name")
        errors = {}

        if not (company_name or "").strip():
            errors["company_name"] = "This field is required."

        if role == "investor":
            if (attrs.get("short_pitch") or "").strip():
                errors["short_pitch"] = "Not allowed for investor."
            if (attrs.get("website") or "").strip():
                errors["website"] = "Not allowed for investor."

        if errors:
            raise serializers.ValidationError(errors)

        email = (attrs.get("email") or "").strip().lower()
        temp_user = User(email=email, username=uuid.uuid4().hex)

        try:
            validate_password(attrs["password"], user=temp_user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        return register_user(validated_data, user_model=User)


# =========================================================
# PROFILE
# =========================================================

class UserStatsMixin(serializers.Serializer):
    stats = serializers.SerializerMethodField()

    def get_stats(self, obj):
        return {
            "projects_count": getattr(obj, "projects_count", 0),
            "followers": getattr(obj, "followers_count", 0),
            "views": getattr(obj, "views_count", 0),
        }


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class PublicProfileSerializer(UserStatsMixin, serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "slug",
            "about_html",
            "short_description",
            "contact",
            "website",
            "tags",
            "stats",
            "media_urls",
            "visibility",
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = User
        fields = (
            "slug",
            "about_html",
            "short_description",
            "contact",
            "website",
            "tags",
            "media_urls",
            "visibility",
        )

    # ---------------- SLUG ----------------

    def validate_slug(self, value: str):
        value = value.strip().lower()
        
        if not value:
            raise serializers.ValidationError("Slug cannot be empty.")

        if not re.match(r"^[a-z0-9-]+$", value):
            raise serializers.ValidationError(
                "Slug may contain only lowercase letters, numbers and hyphens."
            )

        if self.instance and self.instance.slug == value:
            return value

        if User.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already in use.")

        return value


    # ---------------- MEDIA / CONTACT ----------------

    def validate_media_urls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("media_urls must be a list.")

        for url in value:
            if not isinstance(url, str):
                raise serializers.ValidationError("All URLs must be strings.")
            
            parsed = urlparse(url)
            
            if parsed.scheme not in {"http","https"}:
                raise serializers.ValidationError(
                    f"Only http/https URLs are allowed. Invalid URL: {url}"
                )

            if not parsed.scheme or not parsed.netloc:
                raise serializers.ValidationError(
                    f"Invalid URL in media_urls: {url}"
                )
        return value

    def validate_contact(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("contact must be an object.")

        allowed_keys = {"email", "phone", "telegram", "linkedin"}
        unknown_keys = set(value.keys()) - allowed_keys

        if unknown_keys:
            raise serializers.ValidationError(
                f"Unsupported contact fields: {', '.join(unknown_keys)}"
            )

        return value

# ---------------- PUT / PATCH ----------------
    def validate(self, attrs):
        """
        For PUT (partial=False), ensure required fields are present
        """
        if not self.partial:
            required_fields = {"slug"}
            missing = required_fields - set(attrs.keys())
            if missing:
                raise serializers.ValidationError(
                    {field: "This field is required." for field in missing}
                )

        return attrs

    # ---------------- UPDATE ----------------
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        try:
            with transaction.atomic():
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()

                if tags is not None:
                    instance.tags.set(tags)

        except IntegrityError:
            raise serializers.ValidationError(
                {"slug": "This slug is already in use."}
            )

        return instance



# =========================================================
# EMAIL / PASSWORD
# =========================================================

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Email address (not validated for security reasons)",
    )

    def validate_email(self, value):
        return value.lower().strip()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        request = self.context.get("request")
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")
        remember = attrs.get("remember", False)

        user = authenticate(request=request, username=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid credentials.")

        if not user.is_active:
             raise AuthenticationFailed("User inactive or deleted.")

        refresh = RefreshToken.for_user(user)

        if remember:
            refresh.set_exp(lifetime=timedelta(days=7))
        access = refresh.access_token

        if remember:
            access.set_exp(lifetime=timedelta(minutes=30))

        role = getattr(user, "role", None)
        if role is None:
            role = user.groups.first().name if user.groups.exists() else "user"

        return {
            "access": str(access),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": getattr(user, "email", ""),
                "role": role,
            },
        }