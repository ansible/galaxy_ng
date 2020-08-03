from django.db import models

from pulpcore.plugin.models import Task
from pulp_ansible.app.models import AnsibleRepository


class CollectionSyncTask(models.Model):
    repository_id = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-task_id']
