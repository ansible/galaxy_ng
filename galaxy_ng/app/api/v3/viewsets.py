import logging

from django.core.exceptions import ValidationError
from django.urls import reverse

from rest_framework.response import Response

from pulpcore.plugin.models import ContentArtifact, Task
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_views

from galaxy_ng.app.api.base import LocalSettingsMixin
from galaxy_ng.app import models
from .serializers import CollectionVersionSerializer, CollectionUploadSerializer

# from galaxy_ng.app.common import metrics

# hmm, not sure what to do with this
# from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser


log = logging.getLogger(__name__)


class CollectionViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionViewSet):
    pass


class CollectionVersionViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionVersionViewSet):
    serializer_class = CollectionVersionSerializer

    # Custom retrive so we can use the class serializer_class
    # galaxy_ng.app.api.v3.serializers.CollectionVersionSerializer
    # which is responsible for building the 'download_url'. The default pulp one doesn't
    # include the distro base_path which we need (https://pulp.plan.io/issues/6510)
    # so override this so we can use a different serializer
    def retrieve(self, request, *args, **kwargs):
        """
        Returns a CollectionVersion object.
        """
        instance = self.get_object()
        artifact = ContentArtifact.objects.get(content=instance)

        context = self.get_serializer_context()
        context["content_artifact"] = artifact

        serializer = self.get_serializer_class()(instance, context=context)
        return Response(serializer.data)


class CollectionImportViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionImportViewSet):
    pass


class CollectionUploadViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionUploadViewSet):
    # Wrap super().create() so we can create a galaxy_ng.app.models.CollectionImport based on the
    # the import task and the collection artifact details
    def create(self, request, path):

        serializer = CollectionUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        filename = data['filename']

        try:
            namespace = models.Namespace.objects.get(name=filename.namespace)
        except models.Namespace.DoesNotExist:
            raise ValidationError(
                'Namespace "{0}" does not exist.'.format(filename.namespace)
            )

        self.check_object_permissions(request, namespace)

        try:
            response = super(CollectionUploadViewSet, self).create(request, path)
        except ValidationError:
            log.exception('Failed to publish artifact %s (namespace=%s, sha256=%s)',  # noqa
                          data['file'].name, namespace, data.get('sha256'))
            raise

        task_href = response.data['task']

        # icky, have to extract task id from the task_href url
        task_id = task_href.strip("/").split("/")[-1]

        task_detail = Task.objects.get(pk=task_id)

        models.CollectionImport.objects.create(
            task_id=task_detail.pulp_id,
            created_at=task_detail.pulp_created,
            namespace=namespace,
            name=data['filename'].name,
            version=data['filename'].version,
        )

        # TODO: CollectionImport.get_absolute_url() should be able to generate this, but
        #       it needs the  repo/distro base_path for the <path> part of url
        import_obj_url = reverse("galaxy:api:content:v3:collection-import",
                                 kwargs={'pk': str(task_detail.pulp_id),
                                         'path': path})

        log.debug('import_obj_url: %s', import_obj_url)

        return Response(
            data={'task': import_obj_url},
            status=response.status_code
        )
