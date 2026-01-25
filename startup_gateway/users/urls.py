from django.urls import path
from .views import RegisterView, VerifyEmailView, PasswordResetRequestView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
]
