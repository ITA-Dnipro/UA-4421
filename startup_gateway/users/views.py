from django.db import transaction
from rest_framework import status, serializers
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .serializers import RegisterSerializer, LoginSerializer
from .services import send_verification_email, verify_email_token
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

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
    def get(self, request):
        token = request.query_params.get("token", "")
        user = verify_email_token(token)
        if not user:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Email verified."}, status=status.HTTP_200_OK)


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
        serializer_class = LoginSerializer(data=request.data, context={"request": request})
        serializer_class.is_valid(raise_exception=True)
        return Response(serializer_class.validated_data, status=status.HTTP_200_OK)