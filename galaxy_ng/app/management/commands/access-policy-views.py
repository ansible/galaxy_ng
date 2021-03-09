import functools
import json
import logging
import pprint
import re

from django.conf import settings

from django.contrib.admindocs.views import simplify_regex
from django.core.management import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from django_extensions.management.commands import show_urls
from galaxy_ng.app import access_control

log = logging.getLogger(__name__)
pp = pprint.pformat

class Command(show_urls.Command):
    """
    Django management command to show access_policy statements
    """

    help = 'Show access_policy viewsets'

    # def valid_group(self, group):
    #     try:
    #         return Group.objects.get(name=group)
    #     except ObjectDoesNotExist:
    #         raise CommandError(
    #             'Group {} does not exist. Please provide a valid '
    #             'group name.'.format(group))

    # def valid_permission(self, permission):
    #     try:
    #         app_label, codename = permission.split('.', 1)
    #     except ValueError:
    #         raise CommandError(
    #             "Invalid permission format for {}. "
    #             "Expecting 'app_label.codename'.".format(permission)
    #         )
    #     try:
    #         return Permission.objects.get(
    #             content_type__app_label=app_label,
    #             codename=codename)
    #     except ObjectDoesNotExist:
    #         raise CommandError(
    #             "Permission {} not found. Please provide a valid "
    #             "permission in the form 'app_label.codename'".format(
    #                 permission))

    # def add_arguments(self, parser):
    # #     parser.add_argument('group', type=self.valid_group)
    #     parser.add_argument(
    #         '--deployment-mode',
    #         dest='deployment_mode',
    #         default=settings.GALAXY_DEPLOYMENT_MODE,
    #         help="The deployment mode to use the access_policy of. Choices: insights, standalone"
    #     )

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

        view_functions = self.extract_views_from_urlpatterns(urlconf.urlpatterns)
        log.debug('view_functions:\n%s', pp(view_functions))

        for (func, regex, url_name) in view_functions:
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

            format_style = 'json'
            if format_style == 'json':
                views.append({"url": url,
                              "module": module,
                              "name": url_name,
                              "permission_classes": permission_classes,
                              "path_regex": regex,

                              "decorators": decorator})
            else:
                views.append(fmtr.format(
                    module='{0}.{1}'.format(style.MODULE(func.__module__), style.MODULE_NAME(func_name)),
                    url_name=style.URL_NAME(url_name),
                    url=style.URL(url),
                    decorator=decorator,
                ).strip())

        log.debug('views:\n%s', pp(views))


    def not_handle(self, *args, **options):
        ap = access_control.access_policy.AccessPolicyBase()
        deployment_mode = options['deployment_mode']
        statements_map = ap._get_statements(deployment_mode)
        statement_template = \
            "\taction: {action}\n\t\tprincipal: {principal}\n\t\teffect: {effect}\n\t\tconditions:\n{conditions}\n"

        self.stdout.write(f"deployment_mode: {deployment_mode}\n")
        for view, statements in statements_map.items():
            self.stdout.write("%s\n" % view)
            for statement in statements:
                actions = statement['action']
                if isinstance(actions, str):
                    actions = [actions]
                conditions = statement.get('condition', [])
                if isinstance(conditions, str):
                    conditions = [conditions]
                condition_lines = []
                for cond in conditions:
                    condition_line = f'\t\t\t{cond}\n'
                    condition_lines.append(condition_line)
                conditions_buf = ''.join(condition_lines)
                for action in actions:
                    self.stdout.write(statement_template.format(action=action,
                                                                principal=statement['principal'],
                                                                effect=statement['effect'],
                                                                conditions=conditions_buf))
                # self.stdout.write("\t%s\n" % statement)
        # group = options['group']
        # for perm in options['permissions']:
        #     group.permissions.add(perm.id)
        # self.stdout.write("Assigned requested permission to "
        #                   "group '{}'".format(group.name))
