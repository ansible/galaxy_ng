import functools
import logging
import re

from django.conf import settings

from django.contrib.admindocs.views import simplify_regex
from django.core.management import CommandError
from django.core.exceptions import ViewDoesNotExist
from django.urls import URLPattern, URLResolver, resolve, path  # type: ignore
from django.utils import translation
from django.contrib.auth import get_user_model

from django_extensions.management.commands import show_urls
from rest_access_policy import AccessPolicy

log = logging.getLogger(__name__)

UserModel = get_user_model()

EXCLUDE_MODULES = ('pulp', 'admin', 'django',
                   'rest_framework', 'guardian', 'drf_spectacular',
                   'django_prometheus')


class FauxInnerRequest:
    def __init__(self, user, method, path, *args, **kwargs):
        self.method = method
        self.path = path
        self.user = user


class FauxRequest:
    def __init__(self, user, method='GET', path='/faux', *args, **kwargs):
        self.user = user
        self.method = method
        self.path = path
        self.query_params = {}
        self._request = FauxInnerRequest(user, method, path)


class Command(show_urls.Command):
    """
    Django management command to show access_policy statements
    """

    help = 'Show access_policy viewsets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--userid',
            dest='user_id',
            help="The user to test with"
        )
        parser.add_argument(
            '--url',
            dest='url',
            default=None,
            help="The url to show access policy for"
        )
        parser.add_argument(
            '--urlname',
            dest='urlname',
            default=None,
            help="The urlname (eg, 'galaxy:api:content:v3:sync-config')"
                 "to show access policy for"
        )
        parser.add_argument(
            '--url-regex',
            dest='url_regex',
            default='.*',
            help="Only urls that match this regex will be shown. (Default: '.*')"
        )
        super().add_arguments(parser)

    def _get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            # log.exception('Didnt find user_id=%s as a %s', user_id, UserModel)
            return None

        # backends = get_backends()
        # log.debug('backends: %s', backends)
        # backend = backends[0]
        # if isinstance(backend, ModelBackend):
        #     user = backend.get_user(user_id=user_id)

        # try:
        #     user2 = backends[1].get_user(user_id=user_id)
        #     log.debug('user2: %s', user2)
        #     log.debug('user2 type: %s', type(user2))
        # except Exception as exc:
        #     log.exception(exc)

        return user

    def handle(self, *args, **options):
        decorator = options['decorator']
        if not decorator:
            decorator = ['login_required']

        urlconf = options['urlconf']

        views = []
        if not hasattr(settings, urlconf):
            raise CommandError("Settings module {} does not have the attribute {}.".format(settings,
                                                                                           urlconf))

        try:
            urlconf = __import__(getattr(settings, urlconf), {}, {}, [''])
        except Exception as e:
            if options['traceback']:
                import traceback
                traceback.print_exc()
            msg = "Error occurred while trying to load %s: %s" % \
                (getattr(settings, urlconf), str(e))
            raise CommandError(msg)

        url_patterns = urlconf.urlpatterns

        url_filter = options['url']

        url_matcher_re = re.compile(options['url_regex'])

        view_functions = self.extract_views_from_urlpatterns(url_patterns, url_filter=url_filter)

        for (func, regex, url_name, p) in view_functions:
            if hasattr(func, '__globals__'):
                func_globals = func.__globals__
            elif hasattr(func, 'func_globals'):
                func_globals = func.func_globals
            else:
                func_globals = {}

            decorators = [d for d in decorator if d in func_globals]

            if isinstance(func, functools.partial):
                func = func.func
                decorators.insert(0, 'functools.partial')

            permission_classes = []
            if hasattr(func, '__name__'):
                func_name = func.__name__
            elif hasattr(func, '__class__'):
                func_name = '%s()' % func.__class__.__name__
                permission_classes = func.permission_classes
            else:
                func_name = re.sub(r' at 0x[0-9a-f]+', '', repr(func))
                permission_classes = func.permission_classes

            module_base_name = func.__module__
            module = '{0}.{1}'.format(module_base_name, func_name)

            module_name_parts = module_base_name.split('.')
            module_primary_name = module_name_parts[0]

            # log.debug('module_base_name: %s', module_base_name)
            # log.debug('module_name_parts: %s', module_name_parts)

            url_name = url_name or ''
            url = simplify_regex(regex)
            decorator = ', '.join(decorators)

            url_filter = options['url']
            url_name_filter = options['urlname']

            if url_name_filter and url_name_filter != url_name:
                continue

            if module_primary_name in EXCLUDE_MODULES:
                continue

            if url_matcher_re.match(url) is None:
                continue

            perms = []

            if hasattr(func, 'cls'):
                inst = func.cls()
                permission_classes = inst.permission_classes
                perms = inst.get_permissions()

                # FIXME: handle AccessPolicy perm + other perms
                if perms and isinstance(perms[0], AccessPolicy):
                    views.append({"url": url,
                                  "module": module,
                                  "name": url_name,
                                  "permission_classes": permission_classes,
                                  "perms": perms,
                                  "access_policy": perms[0],
                                  "path_regex": regex,
                                  "decorators": decorator,
                                  "view": func.cls,
                                  "p": p})

        for view in views:
            self.show_access_policy(view, **options)

    def extract_views_from_urlpatterns(self, urlpatterns, base='', namespace=None, url_filter=None):
        """
        Return a list of views from a list of urlpatterns.

        Each object in the returned list is a three-tuple: (view_func, regex, name)
        """
        views = []
        if url_filter:
            resolve_match = resolve(url_filter)
            urlpat = path(route=url_filter,
                          view=resolve_match.func,
                          kwargs=resolve_match.kwargs,
                          name=resolve_match.url_name)
            urlpatterns = [urlpat]
        for p in urlpatterns:
            if isinstance(p, (URLPattern, show_urls.RegexURLPattern)):
                try:
                    if not p.name:
                        name = p.name
                    elif namespace:
                        name = '{0}:{1}'.format(namespace, p.name)
                    else:
                        name = p.name

                    pattern = show_urls.describe_pattern(p)
                    # resolved_match = p.resolve(base + pattern)

                    views.append((p.callback, base + pattern, name, p))
                except ViewDoesNotExist:
                    continue
            elif isinstance(p, (URLResolver, show_urls.RegexURLResolver)):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                if namespace and p.namespace:
                    _namespace = '{0}:{1}'.format(namespace, p.namespace)
                else:
                    _namespace = (p.namespace or namespace)
                pattern = show_urls.describe_pattern(p)
                if isinstance(p, show_urls.LocaleRegexURLResolver):
                    for language in self.LANGUAGES:
                        with translation.override(language[0]):
                            views.extend(self.extract_views_from_urlpatterns(patterns,
                                                                             base + pattern,
                                                                             namespace=_namespace))
                else:
                    views.extend(self.extract_views_from_urlpatterns(patterns,
                                                                     base + pattern,
                                                                     namespace=_namespace))
            elif hasattr(p, '_get_callback'):
                try:
                    url_pattern_name = base + show_urls.describe_pattern(p)
                    cb_result = p._get_callback()
                    views.append((cb_result,
                                  url_pattern_name,
                                  p.name,
                                  p,)
                                 )
                except ViewDoesNotExist:
                    continue
            elif hasattr(p, 'url_patterns') or hasattr(p, '_get_url_patterns'):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                views.extend(self.extract_views_from_urlpatterns(patterns,
                                                                 base
                                                                 + show_urls.describe_pattern(p),
                                                                 namespace=namespace))
            else:
                raise TypeError("%s does not appear to be a urlpattern object" % p)
        return views

    def show_access_policy(self, viewset_info, *args, **options):
        access_policy_viewset = viewset_info["view"]
        perms = access_policy_viewset.get_permissions(access_policy_viewset)

        access_perm = perms[0]
        statements = access_perm.get_policy_statements(None, access_policy_viewset)
        statement_template = "\taction: {action}\n\t\tprincipal: {principal}\n\t\t" + \
            "effect: {effect}\n\t\tconditions:\n{conditions}"

        self.stdout.write("%s\n\tviewset: %s\n\turl_name: %s\n" % (viewset_info['url'],
                                                                   viewset_info['module'],
                                                                   viewset_info['name']))
        self.stdout.write("\taccess_policy: %s\n" % (viewset_info['access_policy'],))

        user_id = options['user_id']
        user = self._get_user(user_id)

        if user_id and user is None:
            raise CommandError(f"No user found for user_id={user_id}")

        if user_id:
            self.stdout.write("\tuserid: %s\n" % user_id)
            self.stdout.write("\tusername: %s\n" % user.username)
            self.stdout.write("\tuser is_anonymous: %s\n" % user.is_anonymous)

        self.stdout.write("\n")

        for statement in statements:
            actions = statement['action']
            if isinstance(actions, str):
                actions = [actions]
            conditions = statement.get('condition', [])
            if isinstance(conditions, str):
                conditions = [conditions]
            condition_lines = []
            for cond in conditions:
                condition_line = f'\t\t\t{cond}'
                condition_lines.append(condition_line)
            conditions_buf = '\n'.join(condition_lines) or '\t\t\t[]'
            for action in actions:
                self.stdout.write(statement_template.format(action=action,
                                                            principal=statement['principal'],
                                                            effect=statement['effect'],
                                                            conditions=conditions_buf))
                result = False
                if user and action not in ('*', 'update', 'destroy'):
                    result = self._has_permission(viewset_info, user, action, viewset_info['url'])
                    self.stdout.write(f'\t\tresult: {result}\n')
                self.stdout.write('\n')

    def _has_permission(self, viewset_info, user=None, action=None, url=None):
        view = viewset_info['view']

        amap = {'list': 'GET',
                'retrieve': 'GET',
                'create': 'POST',
                'destroy': 'DELETE',
                'partial_update': 'PATCH',
                'update': 'PUT',
                'move_content': 'POST',
                'sync': 'PUT',
                }
        method = amap.get(action)
        assert method is not None, "action %s is unknown" % action

        request = FauxRequest(user, method=method, path=url)

        view_instance = view(action=action, request=request, kwargs={})

        policy = viewset_info['access_policy']
        result = policy.has_permission(request, view_instance)

        return result
