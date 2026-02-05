from django.http import JsonResponse


def axes_lockout_response(request, response, credentials, *args, **kwargs):
    return JsonResponse(
        {"detail": "Too many login attempts. Try again later.(from axes_lockout)"},
        status=429,
    )
