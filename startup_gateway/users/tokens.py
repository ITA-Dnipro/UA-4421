from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
import hashlib


class PasswordResetTokenGenerator:

    def __init__(self, timeout=3600):
        self.timeout = timeout
        self.signer = TimestampSigner(salt='password-reset')

    def make_token(self, user):
        value = f"{user.pk}:{self._make_hash_value(user)}"
        return self.signer.sign(value)

    def check_token(self, user, token):
        if not user or not token:
            return False

        try:
            unsigned_value = self.signer.unsign(token, max_age=self.timeout)

            parts = unsigned_value.split(':', 1)
            if len(parts) != 2:
                return False

            token_user_id, token_hash = parts

            if str(user.pk) != str(token_user_id):
                return False

            expected_hash = self._make_hash_value(user)
            return token_hash == expected_hash

        except SignatureExpired:
            return False
        except BadSignature:
            return False
        except (ValueError, TypeError):
            return False

    def _make_hash_value(self, user):
        password_hash = user.password

        email = user.email.lower().strip()

        hash_string = f"{password_hash}{email}"
        return hashlib.sha256(hash_string.encode()).hexdigest()


password_reset_token_generator = PasswordResetTokenGenerator(
    timeout=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
)