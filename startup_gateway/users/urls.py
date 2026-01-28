from django.urls import path
from .views import RegisterView, VerifyEmailView, ResendVerificationView, PasswordResetRequestView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
]
