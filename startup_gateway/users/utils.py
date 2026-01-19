import requests
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def validate_recaptcha(token: str) -> bool:
    """
    Validate reCAPTCHA token with Google API
    
    Args:
        token: reCAPTCHA token from frontend
        
    Returns:
        bool: True if validation passed, False otherwise
    """
    if not token:
        logger.warning("Empty reCAPTCHA token provided")
        return False
    
    if not settings.RECAPTCHA_PRIVATE_KEY:
        logger.error("reCAPTCHA private key is not configured")
        # In development, allow without validation
        return settings.DEBUG
    
    try:
        response = requests.post(
            f'https://{settings.RECAPTCHA_DOMAIN}/recaptcha/api/siteverify',
            data={
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': token
            },
            timeout=10  # 10 second timeout
        )
        response.raise_for_status()
        result = response.json()
        
        logger.debug(f"reCAPTCHA validation result: {result}")
        
        # Check if validation passed
        if result.get('success'):
            score = result.get('score', 1.0)  # Score for v3, always 1.0 for v2
            if score >= 0.5:  # Threshold for v3 (v2 always passes)
                logger.info("reCAPTCHA validation successful")
                return True
        
        # Log error codes if any
        error_codes = result.get('error-codes', [])
        if error_codes:
            logger.warning(f"reCAPTCHA validation failed. Error codes: {error_codes}")
        else:
            logger.warning("reCAPTCHA validation failed (no error codes)")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"reCAPTCHA verification request failed: {e}")
        # In production, fail closed. In development, be more permissive
        return settings.DEBUG
    
    return False