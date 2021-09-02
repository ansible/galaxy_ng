from django.db import models
from pulpcore.plugin.models import Task
from pulp_ansible.app.models import AnsibleRepository


class CollectionSyncTask(models.Model):
    repository = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-task__pulp_last_updated']
