from django.db import models

from pulp_ansible.app.models import CollectionVersion

'''
class NGCollection(CollectionVersion):

    #scmref = models.CharField(default="", blank=True, max_length=2000, editable=False)

    class Meta:
        #default_related_name = "%(app_label)s_%(model_name)s"
        default_related_name = "ansible_collectionversion"
'''
