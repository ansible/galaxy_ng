from drf_spectacular.utils import extend_schema
from pulp_ansible.app import serializers as pulp_serializers
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.app.viewsets import AsyncRemoveMixin
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import OperationPostponedResponse

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3.serializers.sync import AnsibleRepositoryDetailSerializer
from galaxy_ng.app.tasks.repository import update_ansible_repository


class AnsibleRepositoryViewSet(AsyncRemoveMixin, api_base.ModelViewSet):
    queryset = AnsibleRepository.objects.all().order_by('name')
    serializer_class = AnsibleRepositoryDetailSerializer
    lookup_field = 'name'
    # SimpleRouter defaults to [^/.]+, which 404s names Tier 1 allows (e.g. foo.bar).
    lookup_value_regex = r'[^/]+'
    permission_classes = [access_policy.AnsibleRepositoryAccessPolicy]
    # Cascaded repository deletes are too heavy to run in the gunicorn worker.
    ALLOW_NON_BLOCKING_DELETE = False

    def get_serializer_class(self):
        # pulpcore general_delete looks up this name in pulp_ansible's serializer
        # registry. Galaxy's detail serializer is not registered there.
        if getattr(self, 'action', None) == 'destroy':
            return pulp_serializers.AnsibleRepositorySerializer
        return super().get_serializer_class()

    def get_object(self):
        # Cache the resolved instance for the lifetime of the request so
        # AsyncRemoveMixin.destroy() doesn't repeat the queryset scoping,
        # name lookup, and object-permission checks that already ran here.
        if not hasattr(self, '_object'):
            self._object = super().get_object()
        return self._object

    def destroy(self, request, *args, **kwargs):
        # AsyncRemoveMixin.destroy() takes a pk URL kwarg; this viewset looks up by name.
        instance = self.get_object()
        return super().destroy(request, pk=str(instance.pk), **kwargs)

    @extend_schema(
        description="Trigger an asynchronous repository update task",
        responses={202: AsyncOperationResponseSerializer},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Queue behind conflicting repository work so save() sees current rows
        # and Pulp can reset last_synced_metadata_time and clean old versions.
        task = dispatch(
            update_ansible_repository,
            exclusive_resources=self.async_reserved_resources(instance),
            args=(instance.pk, request.data, partial),
            immediate=False,
        )
        return OperationPostponedResponse(task, request)

    def get_queryset(self):
        qs = super().get_queryset()
        for permission in self.get_permissions():
            if hasattr(permission, 'scope_queryset'):
                qs = permission.scope_queryset(self, qs)
        return qs
