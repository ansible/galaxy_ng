import logging
import requests

from django.conf import settings
from django.db import transaction
from social_core.backends.github import GithubOAuth2

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import LegacyNamespace


GITHUB_ACCOUNT_SCOPE = 'github'

logger = logging.getLogger(__name__)


def logged(func):
    def wrapper(*args, **kwargs):
        logger.debug(f'LOGGED: {func}')
        res = func(*args, **kwargs)
        logger.debug(f'LOGGED: {func} {res}')
        return res
    return wrapper


# https://github.com/python-social-auth
# https://github.com/python-social-auth/social-core
class GalaxyNGOAuth2(GithubOAuth2):

    @logged
    def get_session_state(self):
        param = self.name + '_state'
        sstate = self.strategy.session_get(param)
        return sstate

    @logged
    def do_auth(self, access_token, *args, **kwargs):
        """Finish the auth process once the access_token was retrieved"""

        # userdata = id, login, access_token
        data = self.get_github_user(access_token)
        if data is not None and 'access_token' not in data:
            data['access_token'] = access_token
        kwargs.update({'response': data, 'backend': self})

        auth_response = self.strategy.authenticate(*args, **kwargs)

        # create a legacynamespace?
        legacy_namespace, _ = self._ensure_legacynamespace(data['login'])

        # create a v3 namespace?

        # add permissiosn to v3 namespace?

        return auth_response

    def _ensure_legacynamespace(self, login):
        """Create an auto legacynamespace for the account"""

        # userdata = id, login, access_token
        user = User.objects.filter(username=login).first()

        # make the namespace
        with transaction.atomic():
            legacy_namespace, created = \
                LegacyNamespace.objects.get_or_create(
                    name=login
                )

            # add the user to the owners
            legacy_namespace.owners.add(user)

        return legacy_namespace, created

    @logged
    def get_github_access_token(self, code):
        baseurl = settings.SOCIAL_AUTH_GITHUB_BASE_URL
        url = baseurl + '/login/oauth/access_token'
        rr = requests.post(
            f'{url}',
            headers={'Accept': 'application/json'},
            json={
                'code': code,
                'client_id': settings.SOCIAL_AUTH_GITHUB_KEY,
                'client_secret': settings.SOCIAL_AUTH_GITHUB_SECRET
            }
        )

        ds = rr.json()
        access_token = ds['access_token']
        return access_token

    @logged
    def get_github_user(self, access_token):
        api_url = settings.SOCIAL_AUTH_GITHUB_API_URL
        url = api_url + '/user'
        rr = requests.post(
            f'{url}',
            headers={
                'Accept': 'application/json',
                'Authorization': f'token {access_token}'
            },
        )
        return rr.json()

    @logged
    def auth_complete(self, *args, **kwargs):
        self.process_error(self.data)

        request = kwargs['request']
        code = request.GET.get('code', None)
        access_token = self.get_github_access_token(code)

        return self.do_auth(
            access_token,
            *args,
            **kwargs
        )
