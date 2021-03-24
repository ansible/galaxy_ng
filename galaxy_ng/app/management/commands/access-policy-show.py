from django.conf import settings

from django.core.management import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from galaxy_ng.app import access_control

class Command(BaseCommand):
    """
    Django management command to show access_policy statements
    """

    help = 'Show access_policy statements'


    def add_arguments(self, parser):
        parser.add_argument(
            '--deployment-mode',
            dest='deployment_mode',
            default=settings.GALAXY_DEPLOYMENT_MODE,
            help="The deployment mode to use the access_policy of. Choices: insights, standalone"
        )

    def handle(self, *args, **options):
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
