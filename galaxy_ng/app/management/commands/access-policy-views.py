import functools
import json
import logging
import pprint
import re

from django.conf import settings

from django.contrib.admindocs.views import simplify_regex
from django.core.management import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ViewDoesNotExist
from django.urls import URLPattern, URLResolver, resolve, path, re_path, reverse # type: ignore
from django.utils import translation
from django.contrib.auth import load_backend, get_backends
from django.contrib.auth.backends import ModelBackend

from django_extensions.management.commands import show_urls
from rest_framework.views import get_view_name
from rest_access_policy import AccessPolicy

from galaxy_ng.app import access_control

log = logging.getLogger(__name__)
pf = pprint.pformat

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
            help="The urlname ('galaxy:api:content:v3:sync-config' for ex) to show access policy for"
        )
        super().add_arguments(parser)

    def _get_user(self, user_id):
        backends = get_backends()
        backend = backends[0]
        if isinstance(backend, ModelBackend):
            user = backend.get_user(user_id=user_id)

        return user

    def handle(self, *args, **options):
        decorator = options['decorator']
        if not decorator:
            decorator = ['login_required']

        urlconf = options['urlconf']

        views = []
        if not hasattr(settings, urlconf):
            raise CommandError("Settings module {} does not have the attribute {}.".format(settings, urlconf))

        try:
            urlconf = __import__(getattr(settings, urlconf), {}, {}, [''])
        except Exception as e:
            if options['traceback']:
                import traceback
                traceback.print_exc()
            raise CommandError("Error occurred while trying to load %s: %s" % (getattr(settings, urlconf), str(e)))


        url_patterns = urlconf.urlpatterns

        url_filter = options['url']

        view_functions = self.extract_views_from_urlpatterns(url_patterns, url_filter=url_filter)
        # log.debug('view_functions:\n%s', pp(view_functions))

        for (func, regex, url_name, p, resolved_match) in view_functions:
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

            module = '{0}.{1}'.format(func.__module__, func_name)
            url_name = url_name or ''
            url = simplify_regex(regex)
            decorator = ', '.join(decorators)

            url_filter = options['url']
            url_name_filter = options['urlname']

            if url_name_filter and url_name_filter != url_name:
                continue

            if module.startswith('admin'):
                continue
            if module.startswith('django'):
                continue
            if module.startswith('rest_framework'):
                continue
            if module.startswith('pulp'):
                continue
            if module.startswith('drf_spectacular'):
                continue

            perms = []

            if hasattr(func, 'cls'):
                permission_classes = func.cls.permission_classes
                perms = func.cls.get_permissions(func.cls)

                # FIXME: handle AccessPolicy perm + other perms
                # access_policy_perm = perms[0]
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
                                  "resolved_match": resolved_match,
                                  "p": p})

            # format_style = 'json'
            # if format_style == 'json':
            #     views.append({"url": url,
            #                   "module": module,
            #                   "name": url_name,
            #                   "permission_classes": permission_classes,
            #                   "perms": perms,
            #                   "path_regex": regex,

            #                   "decorators": decorator})
            # else:
            #     views.append(fmtr.format(
            #         module='{0}.{1}'.format(style.MODULE(func.__module__), style.MODULE_NAME(func_name)),
            #         url_name=style.URL_NAME(url_name),
            #         url=style.URL(url),
            #         decorator=decorator,
            #     ).strip())

        # log.debug('views:\n%s', pp(views))
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
            # log.debug('url_filter %s matched resolve_match: %s', url_filter, resolve_match)
            urlpat = path(route=url_filter,
                          # route=resolve_match.route,
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
                    # log.debug('PATTERN p: %s', p)
                    # log.debug('pattern: %s', pattern)

                    resolved_match = p.resolve(base + pattern)
                    log.debug('resolved_match: %s', resolved_match)

                    views.append((p.callback, base + pattern, name, p, resolved_match))
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
                            views.extend(self.extract_views_from_urlpatterns(patterns, base + pattern, namespace=_namespace))
                else:
                    views.extend(self.extract_views_from_urlpatterns(patterns, base + pattern, namespace=_namespace))
            elif hasattr(p, '_get_callback'):
                try:
                    views.append((p._get_callback(), base + show_urls.describe_pattern(p), p.name, p))
                except ViewDoesNotExist:
                    continue
            elif hasattr(p, 'url_patterns') or hasattr(p, '_get_url_patterns'):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                views.extend(self.extract_views_from_urlpatterns(patterns, base + show_urls.describe_pattern(p), namespace=namespace))
            else:
                raise TypeError("%s does not appear to be a urlpattern object" % p)
        return views


    def show_access_policy(self, viewset_info, *args, **options):
        # ap = access_control.access_policy.AccessPolicyBase()
        # deployment_mode = options['deployment_mode']
        # log.debug('access_policy_viewset: %s is_access_policy: %r', access_policy_viewset, isinstance(access_policy_viewset, AccessPolicy))
        access_policy_viewset = viewset_info["view"]
        perms = access_policy_viewset.get_permissions(access_policy_viewset)
        # log.debug('perms: %s', perms)

        deployment_mode = 'standalone'
        access_perm = perms[0]
        # statements_map = access_perm._get_statements(deployment_mode)
        statements= access_perm.get_policy_statements(None, access_policy_viewset)
        statement_template = \
            "\taction: {action}\n\t\tprincipal: {principal}\n\t\teffect: {effect}\n\t\tconditions:\n{conditions}"

        # self.stdout.write(f"deployment_mode: {deployment_mode}\n")

        view = access_policy_viewset
        self.stdout.write("%s\n\tviewset: %s\n\turl_name: %s\n" % (viewset_info['url'], viewset_info['module'],
                                                                   viewset_info['name']))
        self.stdout.write("\taccess_policy: %s\n" % (viewset_info['access_policy'],))
        self.stdout.write("\tkwargs: %s\n" % (viewset_info['resolved_match'].kwargs,))
        self.stdout.write("\n")

        user_id = options['user_id']
        user = self._get_user(user_id)
        if user_id and user is None:
            raise CommandError(f"No user found for user_id={user_id}")

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
                # self.stdout.write("\t%s\n" % statement)
                result = False
                if user and action not in ('*', 'update', 'destroy'):
                    result = self._has_permission(viewset_info, user, action, viewset_info['url'])
                self.stdout.write(f'\t\tresult: {result}\n')
                self.stdout.write('\n')

        # group = options['group']
        # for perm in options['permissions']:
        #     group.permissions.add(perm.id)
        # self.stdout.write("Assigned requested permission to "
        #                   "group '{}'".format(group.name))

    def _has_permission(self, viewset_info, user=None, action=None, url=None):
        view = viewset_info['view']
        log.debug('pre viewset_info=%s action=%s user=%s url=%s',
                  viewset_info, action, user, url)

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
        log.debug('request: %s request.method: %s', request, request.method)

        # view_instance = view(action=action, request=request)
        # view_instance = view.as_view(actions={'get':'list'})
        # view_instance = view(action=action, request=request, kwargs={'lookup_url_kwarg':'pk'})
        view_instance = view(action=action, request=request, kwargs={})
        log.debug('view_instance: %s', view_instance)

        policy = viewset_info['access_policy']
        result = policy.has_permission(request, view_instance)

        log.debug('view_instance=%s action=%s user=%s url=%s result: %s',
                  view_instance, action, user, url, result)

        return result


