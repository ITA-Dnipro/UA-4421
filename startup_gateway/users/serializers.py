import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework_simplejwt.tokens import RefreshToken

from .services import register_user
from users.models import Role

User = get_user_model()


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
            validate_password(attrs.get("password"), user=temp_user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        return register_user(validated_data, user_model=User)

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


try:
    from axes.handlers.proxy import AxesProxyHandler
except Exception:
    AxesProxyHandler = None


def axes_is_locked(request, identifier: str | None = None) -> bool:
    if not request or AxesProxyHandler is None:
        return False

    cred_key = getattr(settings, "AXES_USERNAME_FORM_FIELD", "username")
    credentials = {cred_key: identifier} if identifier else None
    return AxesProxyHandler.is_locked(request, credentials=credentials)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        request = self.context.get("request")
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")
        remember = attrs.get("remember", False)

        if axes_is_locked(request, email):
            raise Throttled(detail="Too many login attempts. Try again later.")

        user = authenticate(request=request, email=email, password=password)

        if user is None:
            if axes_is_locked(request, email):
                raise Throttled(detail="Too many login attempts. Try again later.")
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