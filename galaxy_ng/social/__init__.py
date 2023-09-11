import logging
import requests

from django.conf import settings
from django.db import transaction
from social_core.backends.github import GithubOAuth2

from galaxy_ng.app.models.auth import Group, User
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils import rbac

from galaxy_importer.constants import NAME_REGEXP


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
        # print('-' * 100)
        # from pprint import pprint
        # pprint(data)
        # print('-' * 100)

        # extract the login now to prevent mutation
        login = data['login']

        # ensure access_token is passed in as a kwarg
        if data is not None and 'access_token' not in data:
            data['access_token'] = access_token

        kwargs.update({'response': data, 'backend': self})

        # use upstream auth method
        auth_response = self.strategy.authenticate(*args, **kwargs)

        # create a legacynamespace?
        legacy_namespace, legacy_created = self._ensure_legacynamespace(login)

        # define namespace, validate and create ...
        namespace_name = self.transform_namespace_name(login)
        print(f'NAMESPACE NAME: {namespace_name}')
        if self.validate_namespace_name(namespace_name):

            # Need user for group and rbac binding
            user = User.objects.filter(username=login).first()

            # Create a group to bind rbac perms.
            group, _ = self._ensure_group(namespace_name, user)

            # create a v3 namespace?
            v3_namespace, v3_created = self._ensure_namespace(namespace_name, user, group)

            # bind the v3 namespace to the v1 namespace
            if legacy_created and v3_created:
                legacy_namespace.namespace = v3_namespace
                legacy_namespace.save()

        return auth_response

    def validate_namespace_name(self, name):
        """Similar validation to the v3 namespace serializer."""

        # galaxy has "extra" requirements for a namespace ...
        # https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
        # NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")

        if not NAME_REGEXP.match(name):
            return False
        if len(name) < 2:
            return False
        if name.startswith('_'):
            return False
        return True

    def transform_namespace_name(self, name):
        """Convert namespace name to valid v3 name."""
        return name.replace('-', '_').lower()

    def _ensure_group(self, namespace_name, user):
        """Create a group in the form of <namespace>:<namespace_name>"""
        with transaction.atomic():
            group, created = \
                Group.objects.get_or_create_identity('namespace', namespace_name)
            if created:
                rbac.add_user_to_group(user, group)
        return group, created

    def _ensure_namespace(self, name, user, group):
        """Create an auto v3 namespace for the account"""

        with transaction.atomic():
            namespace, created = Namespace.objects.get_or_create(name=name)
            print(f'NAMESPACE:{namespace} CREATED:{created}')
            owners = rbac.get_v3_namespace_owners(namespace)
            if created or not owners:
                # Binding by user breaks the UI workflow ...
                # rbac.add_user_to_v3_namespace(user, namespace)
                rbac.add_group_to_v3_namespace(group, namespace)

        return namespace, created

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
            if created:
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
        rr = requests.get(
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
