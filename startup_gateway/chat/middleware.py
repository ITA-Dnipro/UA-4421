"""JWT authentication middleware for WebSocket connections."""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
import jwt
from django.conf import settings


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        token = self.get_token(scope)

        if token:
            scope['user'] = await self.get_user(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    def get_token(self, scope):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        return query_params.get('token', [None])[0]

    @database_sync_to_async
    def get_user(self, token):
        try:
            from users.models import User

            algorithm = settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[algorithm])

            user_id = payload.get('user_id')
            token_version = payload.get('jwt_version', 0)

            user = User.objects.get(id=user_id)

            if user.jwt_version != token_version:
                return AnonymousUser()

            return user

        except jwt.ExpiredSignatureError:
            return AnonymousUser()
        except jwt.InvalidTokenError:
            return AnonymousUser()
        except Exception:
            return AnonymousUser()


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)