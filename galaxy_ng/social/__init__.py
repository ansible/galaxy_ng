import logging
import requests

from django.conf import settings
from django.db import transaction
from social_core.backends.github import GithubOAuth2

# from galaxy_ng.app.models.auth import Group, User
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils import rbac
# from galaxy_ng.app.utils import namespaces as ns_utils

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

        # extract the login now to prevent mutation
        gid = data['id']
        login = data['login']
        email = data['email']

        # ensure access_token is passed in as a kwarg
        if data is not None and 'access_token' not in data:
            data['access_token'] = access_token

        kwargs.update({'response': data, 'backend': self})

        # use upstream auth method to get or create the new user ...
        auth_response = self.strategy.authenticate(*args, **kwargs)

        # make a v3 namespace for the user ...
        v3_namespace, v3_namespace_created = \
            self.handle_v3_namespace(auth_response, email, login, gid)

        print('-' * 100)
        print(f'{login} v3 namespace: {v3_namespace}')
        print('-' * 100)

        # create a legacynamespace and bind to the v3 namespace?
        if v3_namespace:
            legacy_namespace, legacy_namespace_created = \
                self._ensure_legacynamespace(login, v3_namespace)

        return auth_response

    def handle_v3_namespace(self, session_user, session_email, session_login, github_id):

        logger.debug(
            f'HANDLING V3 NAMESPACE session_user:{session_user}'
            + f' session_email:{session_email} session_login:{session_login}'
        )

        namespace_created = False

        # first make the namespace name ...
        namespace_name = self.transform_namespace_name(session_login)

        logger.debug(f'TRANSFORMED NAME: {namespace_name}')
        print(f'TRANSFORMED NAME: {namespace_name}')

        if not self.validate_namespace_name(namespace_name):
            logger.debug(f'DID NOT VALIDATE NAMESPACE NAME: {namespace_name}')
            print(f'DID NOT VALIDATE NAMESPACE NAME: {namespace_name}')
            return False, False

        # does the namespace already exist?
        found_namespace = Namespace.objects.filter(name=namespace_name).first()

        logger.debug(f'FOUND NAMESPACE: {found_namespace}')
        print(f'FOUND NAMESPACE: {found_namespace}')

        # is it owned by this userid?
        if found_namespace:
            logger.debug(f'FOUND EXISTING NAMESPACE: {found_namespace}')
            owners = rbac.get_v3_namespace_owners(found_namespace)
            logger.debug(f'FOUND EXISTING OWNERS: {owners}')

            if session_user in owners:
                return found_namespace, False

        # FIXME - make one from the transformed name?
        if not found_namespace:
            namespace, namespace_created = self._ensure_namespace(namespace_name, session_user)
            return namespace, namespace_created

        # short circuit if the user does own at least one namespace ...
        owned_namespaces = rbac.get_owned_v3_namespaces(session_user)
        logger.debug(f'FOUND USER OWNED NAMESPACES: {owned_namespaces}')
        print(f'FOUND USER OWNED NAMESPACES: {owned_namespaces}')
        if owned_namespaces:
            # does one resemble the desired namespace name?
            owned_namespaces = sorted(owned_namespaces)
            for ns in owned_namespaces:
                if ns.name.startswith(namespace_name):
                    logger.debug(f'MATCHED NS OWNED BY {session_user}: {ns} {ns.name}')
                    return ns, False
            return None, False

        # should always have a namespace ...
        if found_namespace:
            logger.debug(
                f'GENERATING A NEW NAMESPACE NAME SINCE USER DOES NOT OWN {found_namespace}'
            )
            namespace_name = self.generate_available_namespace_name(session_login, github_id)
            logger.debug(f'FINAL NAMESPACE NAME {namespace_name}')

        # create a v3 namespace?
        namespace, namespace_created = self._ensure_namespace(namespace_name, session_user)

        owned = rbac.get_owned_v3_namespaces(session_user)
        logger.debug(f'NS OWNED BY {session_user}: {owned}')

        return namespace, namespace_created

    def generate_available_namespace_name(self, session_login, github_id):
        # we're only here because session_login is already taken as a
        # namespace name and we need a new one for the user

        # this makes the weird gh_{BLAH} name ...
        # namespace_name = ns_utils.map_v3_namespace(session_login)

        # we should iterate and append 0,1,2,3,4,5,etc on the login name
        # until we find one that is free
        counter = -1
        while True:
            counter += 1
            namespace_name = self.transform_namespace_name(session_login) + str(counter)
            if Namespace.objects.filter(name=namespace_name).count() == 0:
                return namespace_name

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

    '''
    def _ensure_group(self, namespace_name, user):
        """Create a group in the form of <namespace>:<namespace_name>"""
        with transaction.atomic():
            group, created = \
                Group.objects.get_or_create_identity('namespace', namespace_name)
            if created:
                rbac.add_user_to_group(user, group)
        return group, created
    '''

    def _ensure_namespace(self, namespace_name, user):
        """Create an auto v3 namespace for the account"""

        with transaction.atomic():
            namespace, created = Namespace.objects.get_or_create(name=namespace_name)
            owners = rbac.get_v3_namespace_owners(namespace)
            if created or not owners:
                # Binding by user breaks the UI workflow ...
                rbac.add_user_to_v3_namespace(user, namespace)

        return namespace, created

    def _ensure_legacynamespace(self, login, v3_namespace):
        """Create an auto legacynamespace for the account"""

        '''
        # userdata = id, login, access_token
        user = User.objects.filter(username=login).first()
        '''

        # make the namespace
        with transaction.atomic():
            legacy_namespace, created = \
                LegacyNamespace.objects.get_or_create(
                    name=login
                )

            # bind the v3 namespace
            if created or not legacy_namespace.namespace:
                legacy_namespace.namespace = v3_namespace
                legacy_namespace.save()

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
