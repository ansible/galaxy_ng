import logging

from pulp_ansible.app.tasks.collections import import_collection
from pulpcore.plugin.models import ContentArtifact

log = logging.getLogger(__name__)

VERSION_CERTIFIED = "certified"


def import_and_auto_approve(artifact_pk, **kwargs):
    """Import collection version and automatically approve.

    Custom task to call pulp_ansible's import_collection() task
    then automatically approve collection version so no
    manual approval action needs to occur.

    Approval currently is a collection version certification flag
    Approval later will be moving from a staging to an approved repo
    """
    import_collection(artifact_pk=artifact_pk, repository_pk=kwargs.get('repository_pk', None))
    content_artifact = ContentArtifact.objects.get(artifact_id=artifact_pk)
    collection_version = content_artifact.content.ansible_collectionversion
    collection_version.certification = VERSION_CERTIFIED
    collection_version.save()
