from django.urls import path
from .views import register, verify_email


urlpatterns = [
    path("register/", register, name="auth-register"),
    path("verify-email/", verify_email, name="auth-verify-email"),
]