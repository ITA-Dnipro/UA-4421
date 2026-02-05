from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
import hashlib


class PasswordResetTokenGenerator:
    """
    Token generator for password reset functionality.

    Tokens automatically invalidate when the user's password changes,
    providing security against token reuse after password reset.
    """

    def __init__(self, timeout=3600):
        self.timeout = timeout
        self.signer = TimestampSigner(salt='password-reset')

    def make_token(self, user):
        """
        Generate a password reset token for a user.

        Token format: timestamp:signature:{user_id}:{hash_value}
        where hash_value is derived from password hash and email.
        """
        value = f"{user.pk}:{self._make_hash_value(user)}"
        return self.signer.sign(value)

    def check_token(self, user, token):
        """
        Validate a password reset token.

        Returns True if token is valid for the given user, False otherwise.
        Token becomes invalid after password change or timeout expiry.
        """
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
        """
        Create a hash value from user's password and email.

        Token invalidates when password changes because the password hash
        is part of the token's hash value. Uses full password hash
        to ensure uniqueness and security.

        Args:
            user: User instance

        Returns:
            SHA256 hash string
        """
        # Use FULL password hash (not just first 40 chars)
        # Django password format: algorithm$salt$hash
        password_hash = user.password

        # Normalize email
        email = user.email.lower().strip()

        # Combine and hash
        hash_string = f"{password_hash}{email}"
        return hashlib.sha256(hash_string.encode()).hexdigest()


# Global instance with timeout from settings
password_reset_token_generator = PasswordResetTokenGenerator(
    timeout=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
)