from django.db import models
from django_lifecycle import LifecycleModel
from pulpcore.plugin.models import AutoDeleteObjPermsMixin, Task
from pulp_ansible.app.models import CollectionRemote, AnsibleRepository

from galaxy_ng.app.access_control import mixins


class CollectionRemoteProxyModel(
    CollectionRemote, LifecycleModel, mixins.GroupModelPermissionsMixin, AutoDeleteObjPermsMixin
):

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        proxy = True


class CollectionSyncTask(models.Model):
    repository = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-task__finished_at']
