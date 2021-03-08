from django.conf import settings

from django.core.management import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from galaxy_ng.app import access_control

class Command(BaseCommand):
    """
    Django management command to show access_policy statements
    """

    help = 'Show access_policy statements'

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
    #     parser.add_argument('group', type=self.valid_group)
    #     parser.add_argument(
    #         'permissions',
    #         nargs='+',
    #         type=self.valid_permission
    #     )

    def handle(self, *args, **options):
        ap = access_control.access_policy.AccessPolicyBase()
        deployment_mode = settings.GALAXY_DEPLOYMENT_MODE
        deployment_mode = 'insights'
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
