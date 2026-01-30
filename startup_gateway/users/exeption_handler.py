from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    resp = exception_handler(exc, context)

    if exc.__class__.__name__ in {"AxesLockout", "AxesBackendPermissionDenied"}:
        return Response(
            {"detail": "Too many login attempts. Try again later."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    return resp