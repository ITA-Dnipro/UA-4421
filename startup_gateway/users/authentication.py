from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class VersionedJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        token_version = validated_token.get('jwt_version', 0)

        if user.jwt_version != token_version:
            raise AuthenticationFailed(
                detail='Your session has been invalidated due to a password change. Please log in again.',
                code='token_invalidated'
            )

        return user
