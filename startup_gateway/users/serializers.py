import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
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

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Email address (not validated for security reasons)"
    )

    def validate_email(self, value):
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(
        required=True,
        help_text="Base64-encoded user ID from reset email"
    )
    token = serializers.CharField(
        required=True,
        help_text="Password reset token from email"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        help_text="New password (min 8 characters)"
    )

    def validate_uid(self, value):
        try:
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str
            uid = force_str(urlsafe_base64_decode(value))
            return uid
        except (ValueError, TypeError, OverflowError):
            raise serializers.ValidationError("Invalid user ID.")

    def validate(self, attrs):
        uid = attrs.get('uid')
        token = attrs.get('token')
        new_password = attrs.get('new_password')

        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"uid": "Invalid user ID."})

        from .tokens import password_reset_token_generator
        if not password_reset_token_generator.check_token(user, token):
            raise serializers.ValidationError({
                "token": "Invalid or expired token."
            })

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                "new_password": list(e.messages)
            })

        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return user
