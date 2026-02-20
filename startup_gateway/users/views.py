from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

import logging

from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from .serializers import RegisterSerializer, VerifyEmailSerializer, ResendVerificationSerializer, PasswordResetRequestSerializer, LoginSerializer, PasswordResetConfirmSerializer
from .services import send_verification_email, verify_email_token, is_resend_verification_throttled
from .tokens import password_reset_token_generator
from .email_service import PasswordResetEmailService
from .models import PasswordResetAttempt, User, PasswordResetConfirmation

logger = logging.getLogger(__name__)
User = get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
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
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Email verified."}, status=status.HTTP_200_OK)

    def get(self, request):
        token = request.query_params.get("token", "")
        user = verify_email_token(token)
        if not user:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Email verified."}, status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        ip = request.META.get("REMOTE_ADDR", "")

        if is_resend_verification_throttled(email="", ip=ip):
            return Response(
                {"detail": "If the email address is valid, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user or getattr(user, "verified", False):
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
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "If the email exists, you will receive reset instructions."},
                status=status.HTTP_200_OK
            )

        email = serializer.validated_data['email']
        ip_address = get_client_ip(request)

        user = User.objects.filter(email=email, is_active=True).first()
        token_sent = False

        if user:
            token = password_reset_token_generator.make_token(user)
            token_sent = PasswordResetEmailService.send_reset_email(
                user=user,
                token=token,
                request=request
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
            status=status.HTTP_200_OK
        )


@extend_schema(
    request=LoginSerializer,
    responses={
        200: inline_serializer(
            name="LoginResponse",
            fields={
                "access": serializers.CharField(),
                "refresh": serializers.CharField(),
                "user": inline_serializer(
                    name="LoginUser",
                    fields={
                        "id": serializers.IntegerField(),
                        "email": serializers.EmailField(),
                        "role": serializers.CharField(),
                    },
                ),
            },
        ),
        401: OpenApiResponse(
            description="Invalid credentials / inactive user",
            response=inline_serializer(
                name="LoginError401",
                fields={"detail": serializers.CharField()},
            ),
        ),
        400: OpenApiResponse(
            description="Validation error",
            response=inline_serializer(
                name="LoginError400",
                fields={"detail": serializers.CharField()},
            ),
        ),
    },
    tags=["Auth"],
    summary="Login",
)

class LoginView(APIView):
    throttle_classes = [AnonRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        django_request = getattr(request, "_request", request)

        serializer = LoginSerializer(
            data=request.data,
            context={"request": django_request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'password_reset_confirm'

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        user_for_logging = None
        
        # Try to decode uid for logging purposes
        uid_raw = request.data.get("uid")
        if uid_raw:
            try:
                from django.utils.http import urlsafe_base64_decode
                from django.utils.encoding import force_str
                uid = force_str(urlsafe_base64_decode(uid_raw))
                user_for_logging = User.objects.filter(pk=uid).first()
            except Exception:
                user_for_logging = None

        # Validate the serializer
        if not serializer.is_valid():
            failure_reason = self._categorize_error_internal(serializer.errors, user_for_logging)
            try:
                PasswordResetConfirmation.objects.create(
                    user=user_for_logging,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason=failure_reason,
                )
            except Exception as e:
                logger.error(f"Failed to log password reset failure: {e}")

            # Password validation errors return 422 with specific error details
            if "password" in serializer.errors:
                # Check if it's a required field error vs validation error
                password_errors = serializer.errors["password"]
                has_required = any('required' in str(err).lower() for err in password_errors)
                if has_required:
                    # Missing password returns 422 (validation error)
                    return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                # Weak password returns 422 with details
                return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # Missing token or uid returns 400 (generic security error)
            if "token" in serializer.errors or "uid" in serializer.errors:
                return Response(
                    {"detail": "Invalid or expired password reset link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Non-field errors (validation failures) return 400 with generic message
            if "non_field_errors" in serializer.errors:
                return Response(
                    {"detail": "Invalid or expired password reset link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Default: return errors with 422
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            user = serializer.save(ip_address=ip_address, user_agent=user_agent)
        except Exception as e:
            logger.error(f"Failed to complete password reset transaction: {e}")
            return Response(
                {"detail": "An error occurred while resetting your password. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK
        )

    def _categorize_error_internal(self, errors, user):
        if 'password' in errors:
            return 'weak_password'

        # Check for required field errors
        if 'uid' in errors or 'token' in errors:
            uid_errors = errors.get('uid', [])
            token_errors = errors.get('token', [])
            
            # Check if these are "required" field errors
            has_uid_required = any('required' in str(err).lower() for err in uid_errors)
            has_token_required = any('required' in str(err).lower() for err in token_errors)
            
            if has_uid_required or has_token_required:
                return 'missing_required_fields'

        # Check for non-field validation errors
        if 'non_field_errors' in errors:
            error_str = str(errors['non_field_errors']).lower()
            if 'invalid or expired' in error_str:
                return 'invalid_token' if user else 'invalid_uid_format'

        return 'validation_error'
