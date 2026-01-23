from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer
from .services import send_verification_email, verify_email_token


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, created, should_send_email = serializer.save()

        if should_send_email:
            transaction.on_commit(lambda: send_verification_email(user))

        return Response(
            {
                "detail": "If the email address is valid, a verification email has been sent."
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        user = verify_email_token(token)
        if not user:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Email verified."}, status=status.HTTP_200_OK)
