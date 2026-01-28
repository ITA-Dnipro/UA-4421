from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from datetime import datetime


class CustomPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def __init__(self, timeout):
        self.timeout = timeout
        super().__init__()

    def _num_seconds(self, dt):
        epoch = datetime(2001, 1, 1)
        return int((dt - epoch).total_seconds())


password_reset_token_generator = CustomPasswordResetTokenGenerator(
    timeout=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
)
