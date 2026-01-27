from django.urls import path
from .views import RegisterView, VerifyEmailView, LoginView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),

    path("login/", LoginView.as_view(), name="auth-login"),
]
