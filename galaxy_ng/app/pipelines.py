from django.conf import settings
from django.contrib.auth.models import Group


def user_role(response, details, user=None, *args, **kwargs):
    """Pipeline used by SOCIAL AUTH to associate superuser priviledges."""
    if not user:
        return

    roles = response.get(settings.KEYCLOAK_ROLE_TOKEN_CLAIM, [])
    if not roles:
        return

    if not isinstance(roles, list):
        return

    is_admin = False
    if settings.KEYCLOAK_ADMIN_ROLE in roles:
        is_admin = True

    user.is_staff = is_admin
    user.is_admin = is_admin
    user.is_superuser = is_admin
    user.save()


def user_group(response, details, user=None, *args, **kwargs):
    """Pipeline used by social auth to update a users group associations."""
    if not user:
        return

    group_list = response.get(settings.KEYCLOAK_GROUP_TOKEN_CLAIM, [])

    if not isinstance(group_list, list):
        return

    groups = []
    for group_name in group_list:
        group_name_split = group_name.split("/")
        group_name = group_name_split[-1]
        new_group, created = Group.objects.get_or_create(name=group_name)
        groups.append(new_group)

    user.groups.clear()

    for group_item in groups:
        group_item.user_set.add(user)
