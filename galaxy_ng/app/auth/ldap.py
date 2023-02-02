from django_auth_ldap.backend import LDAPBackend
from pulpcore.plugin.models import role as role_models
from django.contrib.contenttypes.models import ContentType


class PulpLDAPBackend(LDAPBackend):
    """
    Extends LDAP backend to make it work with pulp roles.
    """

    def _get_permissions_from_roles(self, user, obj):
        groups = user.ldap_user.group_names
        permissions = set()
        qs = role_models.GroupRole.objects.filter(group__name__in=groups)
        if obj is not None:
            obj_type = ContentType.objects.get_for_model(obj)
            qs.filter(object_id=obj.pk, content_type=obj_type)
        else:
            qs.filter(object_id=None)

        for group_role in qs:
            perms = group_role.role.permissions.all()
            perms = perms.values_list("content_type__app_label", "codename")

            permissions.update({"{}.{}".format(ct, name) for ct, name in perms})
        return permissions


    def get_group_permissions(self, user, obj=None):
        # TODO: this should be disabled when FIND_GROUP_PERMS is off



        
        # attach the _group_permissions attribute to the ldap user
        if hasattr(user, "ldap_user"):
            if user.ldap_user._group_permissions is None:
                user.ldap_user._group_permissions = self._get_permissions_from_roles(user, None)

            if obj:
                return user.ldap_user._group_permissions.union(self._get_permissions_from_roles(user, obj))

        return super().get_group_permissions(user, obj=obj)
