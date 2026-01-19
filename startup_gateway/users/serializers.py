"""
Serializers for users app - UA-4421 Security Implementation
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .utils import validate_recaptcha

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with reCAPTCHA protection (UA-4421)
    Adds reCAPTCHA validation to the existing model
    """
    captcha_token = serializers.CharField(
        write_only=True,
        required=True,
        help_text="reCAPTCHA token obtained from frontend"
    )
    
    class Meta:
        model = User  # Using EXISTING model
        fields = ['email', 'password', 'captcha_token']  # Adding only necessary fields
        # If there are other fields in the model for registration - add them here
    
    def validate(self, attrs):
        """
        Validate reCAPTCHA token before user creation
        """
        validated_data = super().validate(attrs)
        
        # Get and validate reCAPTCHA token
        captcha_token = attrs.get('captcha_token')
        
        if not validate_recaptcha(captcha_token):
            raise serializers.ValidationError({
                'captcha_token': 'Please complete the reCAPTCHA verification'
            })
        
        # Remove token from data (not needed in database)
        attrs.pop('captcha_token', None)
        
        return validated_data