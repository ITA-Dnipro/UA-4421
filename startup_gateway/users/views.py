import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.serializers import (
    RegisterSerializer,
    VerifyEmailSerializer,
    ResendVerificationSerializer,
    PasswordResetRequestSerializer,
    PublicProfileSerializer,
    ProfileUpdateSerializer,
)
from users.services import (
    send_verification_email,
    verify_email_token,
    is_resend_verification_throttled,
)
from users.tokens import password_reset_token_generator
from users.email_service import PasswordResetEmailService
from users.permissions import IsOwnerOrReadOnly
from users.models import PasswordResetAttempt

logger = logging.getLogger(__name__)
User = get_user_model()


# =========================================================
# HELPERS
# =========================================================

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# =========================================================
# AUTH
# =========================================================

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, created, should_send_email = serializer.save()

        if should_send_email:
            transaction.on_commit(lambda: send_verification_email(user))

        return Response(
            {"detail": "If the email address is valid, a verification email has been sent."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get("token", "")
        user = verify_email_token(token)
        if not user:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Email verified."},
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        token = request.query_params.get("token", "")
        user = verify_email_token(token)
        if not user:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Email verified."},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        ip = get_client_ip(request)

        if is_resend_verification_throttled(email="", ip=ip):
            return Response(
                {"detail": "If the email address is valid, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user or user.verified:
            return Response(
                {"detail": "If the email address is valid, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )

        if is_resend_verification_throttled(email=email, ip=""):
            return Response(
                {"detail": "If the email address is valid, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )

        send_verification_email(user)

        return Response(
            {"detail": "If the email address is valid, a verification email has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"detail": "If the email exists, you will receive reset instructions."},
                status=status.HTTP_200_OK,
            )

        email = serializer.validated_data["email"]
        ip_address = get_client_ip(request)

        user = User.objects.filter(email=email, is_active=True).first()
        token_sent = False

        if user:
            token = password_reset_token_generator.make_token(user)
            token_sent = PasswordResetEmailService.send_reset_email(
                user=user,
                token=token,
                request=request,
            )

            if token_sent:
                logger.info(f"Password reset email sent to {email}")

        try:
            PasswordResetAttempt.objects.create(
                user=user,
                email=email,
                ip_address=ip_address,
                token_sent=token_sent,
            )
        except Exception as e:
            logger.error(f"Failed to log password reset attempt: {e}")

        return Response(
            {"detail": "If the email exists, you will receive reset instructions."},
            status=status.HTTP_200_OK,
        )


# =========================================================
# PROFILE
# =========================================================

class ProfileDetailUpdateView(APIView):
    """
    GET    /api/profiles/{id}/
    PATCH  /api/profiles/{id}/
    PUT    /api/profiles/{id}/
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        return [
            IsAuthenticated(),
            IsOwnerOrReadOnly(),
        ]

    def get_object(self, id):
        return get_object_or_404(User, id=id)

    def get(self, request, id):
        user = self.get_object(id)

        if not user.visibility:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = PublicProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        user = self.get_object(id)
        self.check_object_permissions(request, user)

        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=False,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
