import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework import exceptions


class ExpiringTokenAuthentication(TokenAuthentication):

    def authenticate_credentials(self, key):
        try:
            token = Token.objects.get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        # Token expiration only for SOCIAL AUTH users
        if hasattr(token.user, 'social_auth'):
            from social_django.models import UserSocialAuth
            try:
                token.user.social_auth.get(provider="keycloak")
                utc_now = timezone.now()
                # Set default to one day expiration
                try:
                    expiry = int(settings.get('GALAXY_TOKEN_EXPIRATION'))
                    if token.created < utc_now - datetime.timedelta(minutes=expiry):
                        raise exceptions.AuthenticationFailed('Token has expired')
                except ValueError:
                    pass
                except TypeError:
                    pass
            except UserSocialAuth.DoesNotExist:
                pass

        return (token.user, token)
