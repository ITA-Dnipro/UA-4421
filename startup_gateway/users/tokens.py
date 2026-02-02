from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings


class PasswordResetTokenGenerator:

    def __init__(self, timeout=3600):

        self.timeout = timeout
        self.signer = TimestampSigner()

    def make_token(self, user):

        return self.signer.sign(user.pk)

    def check_token(self, user, token):

        if not user or not token:
            return False

        try:
            user_id = self.signer.unsign(token, max_age=self.timeout)

            return str(user.pk) == str(user_id)

        except SignatureExpired:
            return False
        except BadSignature:
            return False
        except (ValueError, TypeError):
            return False


password_reset_token_generator = PasswordResetTokenGenerator(
    timeout=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
)
