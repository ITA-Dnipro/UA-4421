from django.urls import path
from .views import RegisterView, VerifyEmailView, ResendVerificationView, PasswordResetRequestView, LoginView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path("login/", LoginView.as_view(), name="auth-login"),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
