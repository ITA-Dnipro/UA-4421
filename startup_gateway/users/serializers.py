from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from investors.models import InvestorProfile
from startups.models import StartupProfile
from users.models import Role

import uuid

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
    
    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"].strip().lower()
        role_name = validated_data["role"].strip().lower()
        company_name = validated_data["company_name"]
        short_pitch = validated_data.get("short_pitch", "")
        website = validated_data.get("website", "")
        phone = validated_data.get("contact_phone", "")

        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            should_send_email = not getattr(existing, "verified", False)
            return existing, False, should_send_email

        user = User(
            username=uuid.uuid4().hex,
            email=email,
            phone=phone,
            verified=False,
            is_active=False,
        )
        user.set_password(validated_data["password"])
        user.save()

        role_obj, _ = Role.objects.get_or_create(name=role_name)
        user.roles.add(role_obj)

        if role_name == "startup":
            StartupProfile.objects.create(
                user=user,
                company_name=company_name,
                short_pitch=short_pitch,
                website=website,
            )
        else:
            InvestorProfile.objects.create(
                user=user,
                company_name=company_name,
            )

        return user, True, True


