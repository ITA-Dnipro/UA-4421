import uuid

from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .services import register_user
from users.models import Role
from django.db import transaction
from django.db.models import F
from .models import PasswordResetConfirmation
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


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

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Email address (not validated for security reasons)"
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


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(
        required=True,
        help_text="Base64-encoded user ID from reset email"
    )
    token = serializers.CharField(
        required=True,
        help_text="Password reset token from email"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        help_text="New password (min 8 characters)"
    )

    def validate(self, attrs):
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from .tokens import password_reset_token_generator

        uid_encoded = attrs.get('uid')
        token = attrs.get('token')
        password = attrs.get('password')

        generic_error = "Invalid or expired password reset link."

        try:
            uid = force_str(urlsafe_base64_decode(uid_encoded))
        except (ValueError, TypeError, OverflowError):
            raise serializers.ValidationError(generic_error)

        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError(generic_error)

        if not password_reset_token_generator.check_token(user, token):
            raise serializers.ValidationError(generic_error)

        try:
            validate_password(password, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                "password": list(e.messages)
            })

        attrs['user'] = user
        return attrs

    def save(self, ip_address=None):
        user = self.validated_data['user']
        password = self.validated_data['password']

        with transaction.atomic():
            user.set_password(password)
            user.jwt_version = F('jwt_version') + 1
            user.save(update_fields=['password', 'jwt_version'])
            user.refresh_from_db(fields=['jwt_version'])

        if ip_address is not None:
            try:
                PasswordResetConfirmation.objects.create(
                    user=user,
                    ip_address=ip_address,
                    success=True,
                    failure_reason=None
                )
            except Exception as e:
                logger.error(f"Failed to create password reset audit log: {e}")

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['jwt_version'] = user.jwt_version

        return token
