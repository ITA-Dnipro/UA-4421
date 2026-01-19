from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.conf import settings
import logging

from .serializers import RegisterSerializer

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key='ip', rate=settings.RATE_LIMIT_REGISTRATION, method='POST'), name='post')
@method_decorator(ratelimit(key='user', rate=settings.RATE_LIMIT_REGISTRATION, method='POST'), name='post')
class RegisterView(generics.CreateAPIView):
    """
    User registration view with reCAPTCHA and rate limiting (UA-4421)
    
    Features:
    - reCAPTCHA v2 validation
    - Rate limiting: 5 attempts per minute per IP
    - Rate limiting: 5 attempts per minute per user/email
    - Error handling with logging
    - Configuration endpoint for frontend
    """
    serializer_class = RegisterSerializer
    permission_classes = []  # Allow anyone to register
    
    def get(self, request, *args, **kwargs):
        """
        GET: Return security configuration for frontend
        Useful for frontend to get reCAPTCHA key and rate limits
        """
        return Response({
            'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY,
            'rate_limits': {
                'registration': settings.RATE_LIMIT_REGISTRATION,
                'resend': settings.RATE_LIMIT_RESEND
            },
            'security_features': {
                'recaptcha': True,
                'rate_limiting': True,
                'cors': True
            }
        })
    
    def post(self, request, *args, **kwargs):
        """
        POST: Handle user registration with security checks
        
        Request body should contain:
        - email: string
        - password: string  
        - captcha_token: string (from Google reCAPTCHA)
        """
        try:
            response = super().post(request, *args, **kwargs)
            
            # Log successful registration (without sensitive data)
            email = request.data.get('email', 'unknown')
            logger.info(f"Successful registration for: {email}")
            
            return response
            
        except Exception as e:
            # Log the error for monitoring
            logger.error(f"Registration failed: {str(e)}")
            
            # Return user-friendly error message
            return Response(
                {
                    'error': 'Registration failed. Please try again.',
                    'details': 'Check your information and reCAPTCHA.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class HealthCheckView(APIView):
    """
    Simple health check endpoint for monitoring
    """
    permission_classes = []
    
    def get(self, request, *args, **kwargs):
        """
        GET: Return service health status
        """
        return Response({
            'status': 'healthy',
            'service': 'users',
            'security': {
                'recaptcha_configured': bool(settings.RECAPTCHA_PUBLIC_KEY),
                'rate_limiting_enabled': True
            }
        })


# For future use - password reset with rate limiting
@method_decorator(ratelimit(key='ip', rate=settings.RATE_LIMIT_RESEND, method='POST'), name='post')
class PasswordResetView(APIView):
    """
    Password reset request view with rate limiting
    Will be implemented in future phases
    """
    permission_classes = []
    
    def post(self, request, *args, **kwargs):
        return Response({
            'message': 'Password reset endpoint (to be implemented)',
            'rate_limit': settings.RATE_LIMIT_RESEND
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
