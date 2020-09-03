from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from pulpcore.plugin.models import Task
from pulp_ansible.app.models import AnsibleRepository, Collection

from .namespace import Namespace


@receiver(post_save, sender=Collection)
def create_namespace_if_not_present(sender, instance, created, **kwargs):
    """Ensure Namespace object exists when Collection object saved.

    django signal for pulp_ansible Collection model, so that whenever a
    Collection object is created or saved, it will create a Namespace object
    if the Namespace does not already exist.

    Supports use case: In pulp_ansible sync, when a new collection is sync'd
    a new Collection object is created, but the Namespace object is defined
    in galaxy_ng and therefore not created. This signal ensures the
    Namespace is created.
    """

    Namespace.objects.get_or_create(name=instance.namespace)


class CollectionSyncTask(models.Model):
    repository = models.ForeignKey(AnsibleRepository, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-task__finished_at']
