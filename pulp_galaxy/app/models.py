"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    ContentArtifact,
    Remote,
    Repository,
    Publication,
    PublicationDistribution,
)

logger = getLogger(__name__)


class GalaxyContent(Content):
    """
    The "galaxy" content type.

    Define fields you need for your new content type and
    specify uniqueness constraint to identify unit of this type.

    For example::

        field1 = models.TextField()
        field2 = models.IntegerField()
        field3 = models.CharField()

        class Meta:
            default_related_name = "%(app_label)s_%(model_name)s"
            unique_together = (field1, field2)
    """

    TYPE = "galaxy"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class GalaxyPublication(Publication):
    """
    A Publication for GalaxyContent.

    Define any additional fields for your new publication if needed.
    """

    TYPE = "galaxy"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class GalaxyRemote(Remote):
    """
    A Remote for GalaxyContent.

    Define any additional fields for your new remote if needed.
    """

    TYPE = "galaxy"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class GalaxyRepository(Repository):
    """
    A Repository for GalaxyContent.

    Define any additional fields for your new repository if needed.
    """

    TYPE = "galaxy"

    CONTENT_TYPES = [GalaxyContent]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class GalaxyDistribution(PublicationDistribution):
    """
    A Distribution for GalaxyContent.

    Define any additional fields for your new distribution if needed.
    """

    TYPE = "galaxy"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
