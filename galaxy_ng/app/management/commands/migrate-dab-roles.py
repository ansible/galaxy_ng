from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):

        print("Migrating role definitions for DAB ...")

        # from django.contrib.auth.models import Permission
        from pulpcore.plugin.models.role import Role
        from ansible_base.rbac.models import RoleDefinition
        from ansible_base.rbac.models import DABPermission

        # The UI code is the only place I could find the descriptions for the roles ...
        # https://github.com/ansible/ansible-hub-ui/blob/364d9af2d80d2defecfab67f44706798b8d2cf83/src/utilities/translate-locked-role.ts#L9
        galaxy_role_description = {
            'core.task_owner': 'Allow all actions on a task.',
            'core.taskschedule_owner': 'Allow all actions on a task schedule.',
            'galaxy.ansible_repository_owner': 'Manage ansible repositories.',
            'galaxy.collection_admin': (
                'Create, delete and change collection namespaces. '
                + 'Upload and delete collections. Sync collections from remotes.'
                + ' Approve and reject collections.'
            ),
            'galaxy.collection_curator': 'Approve, reject and sync collections from remotes.',
            'galaxy.collection_namespace_owner': 'Change and upload collections to namespaces.',
            'galaxy.collection_publisher': 'Upload and modify collections.',
            'galaxy.collection_remote_owner': 'Manage collection remotes.',
            'galaxy.content_admin': 'Manage all content types.',
            'galaxy.execution_environment_admin': (
                'Push, delete and change execution environments.'
                + ' Create, delete and change remote registries.'
            ),
            'galaxy.execution_environment_collaborator': 'Change existing execution environments.',
            'galaxy.execution_environment_namespace_owner':
                'Create and update execution environments under existing container namespaces.',
            'galaxy.execution_environment_publisher': 'Push and change execution environments.',
            'galaxy.group_admin': 'View, add, remove and change groups.',
            'galaxy.synclist_owner': 'View, add, remove and change synclists.',
            'galaxy.task_admin': 'View and cancel any task.',
            'galaxy.user_admin': 'View, add, remove and change users.',
        }

        # make an index of all current dab permissions ...
        dabperm_map = {}
        for dabperm in DABPermission.objects.all():
            perm_codename = dabperm.codename
            ctype_model = dabperm.content_type.model
            app_label = dabperm.content_type.app_label
            dabperm_map[(app_label, ctype_model, perm_codename)] = dabperm

        # copy all of the galaxy roles to dab roledefinitions ...
        for role in Role.objects.all():
            role_name = role.name
            role_description = galaxy_role_description.get(role_name, '')
            print(f'{role_name} ... {role_description}')

            # find the related permissions based on app name and permission name ...
            related_perms = []

            # find all the related content types from the permissions ...
            ctypes = []

            for perm in role.permissions.all():

                app_name = perm.content_type.app_label
                perm_name = perm.codename
                ctypes.append((perm.content_type_id, perm.content_type))

                for k, v in dabperm_map.items():
                    if k[0] == app_name and k[2] == perm_name:
                        related_perms.append(v)
                        break

            # we need ALL of the necessary permissions ...
            if len(related_perms) != role.permissions.count():
                print(f"didn't find all the permissions for {role_name}")
                continue

            # get or make the def ...
            rd, created = RoleDefinition.objects.get_or_create(name=role_name)
            if created:
                print('\tcreated')

            # set the description for the UI ...
            rd.description = role_description

            # add each related permission ...
            for rperm in related_perms:
                if not rd.permissions.filter(id=rperm.id).exists():
                    print(f'\tadd {rperm}')
                    rd.permissions.add(rperm)

            # what are all the content types involved ... ?
            ctypes = sorted(set(ctypes))
            if len(ctypes) == 1:
                if rd.content_type_id != ctypes[0][1]:
                    print(f'\tsetting {role_name} content type to {ctypes[0][1]}')
                    rd.content_type_id = ctypes[0][1]
                    rd.content_type = ctypes[0][1]

            rd.save()
