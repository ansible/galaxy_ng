
from django_lifecycle import LifecycleModel
from pulpcore.plugin.models import AutoDeleteObjPermsMixin
from pulp_ansible.app.models import CollectionRemote

from galaxy_ng.app.access_control import mixins


class CollectionRemoteProxyModel(
    CollectionRemote, LifecycleModel, mixins.GroupModelPermissionsMixin, AutoDeleteObjPermsMixin
):

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        proxy = True
