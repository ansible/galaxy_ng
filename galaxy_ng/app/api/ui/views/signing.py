from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from pulp_ansible.app.models import AnsibleDistribution
from pulpcore.plugin.models import SigningService
from rest_framework import status
from rest_framework.response import Response

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.tasks import call_sign_task


class CollectionSignView(api_base.APIView):
    action = "sign"
    permission_classes = [access_policy.CollectionAccessPolicy]

    def post(self, request, *args, **kwargs):
        """Creates a signature for the content units specified in the request.


        Base URL: _ui/v1/collection_signing/

        Optional URLS:
        - _ui/v1/collection_signing/<distro_base_path>/
        - _ui/v1/collection_signing/<distro_base_path>/<namespace>/
        - _ui/v1/collection_signing/<distro_base_path>/<namespace>/<collection>/
        - _ui/v1/collection_signing/<distro_base_path>/<namespace>/<collection>/<version>/

        The request body should contain a JSON object with the following keys:

        Required
            - signing_service: The name of the signing service to use
            - distro_base_path: The name of the distro_base_path to add the signatures
              (if not provided via URL)

        Optional
            - content_units: A list of content units UUIDS to be signed.
            (if content_units is ["*"], all units under the repo will be signed)
            OR
            - namespace: Namespace name (if not provided via URL)
            (if only namespace is specified, all collections under that namespace will be signed)

        Optional (one or more)
            - collection: Collection name (if not provided via URL)
            (if collection name is added, all versions under that collection will be signed)
            - version: The version of the collection to sign (if not provided via URL)
            (if version is specified, only that version will be signed)
        """

        self.kwargs = kwargs
        signing_service = self._get_signing_service(request)
        repository = self.get_repository(request)
        content_units = self._get_content_units_to_sign(request, repository)

        sign_task = call_sign_task(signing_service, repository, content_units)
        return Response(data={"task_id": sign_task.pk}, status=status.HTTP_202_ACCEPTED)

    def _get_content_units_to_sign(self, request, repository):
        """Returns a list of pks for content units to sign.

        If `content_units` is specified in the request, it will be used.
        Otherwise, will use the filtering options specified in the request.
        namespace, collection, version can be used to filter the content units.
        """
        if request.data.get("content_units"):
            return request.data["content_units"]
        else:
            try:
                namespace = self.kwargs.get("namespace") or request.data["namespace"]
            except KeyError:
                raise ValidationError(_("Missing required field: namespace"))

            query_params = {
                "pulp_type": "ansible.collection_version",
                "ansible_collectionversion__namespace": namespace,
            }

            collection = self.kwargs.get("collection") or request.data.get("collection")
            version = self.kwargs.get("version") or request.data.get("version")

            if collection:
                query_params["ansible_collectionversion__name"] = collection
            if version:
                query_params["ansible_collectionversion__version"] = version

            content_units = repository.content.filter(**query_params).values_list("pk", flat=True)
            if not content_units:
                raise ValidationError(_("No content units found for: %s") % query_params)

            return [str(item) for item in content_units]

    def get_repository(self, request):
        """Retrieves the repository object from the request distro_base_path.

        :param request: the request object
        :return: the repository object

        NOTE: This method is used by the access policies.
        """
        try:
            distro_name = self.kwargs.get("path") or request.data["distro_base_path"]
        except KeyError:
            raise ValidationError(_("distro_base_path field is required."))

        try:
            return AnsibleDistribution.objects.get(base_path=distro_name).repository
        except ObjectDoesNotExist:
            raise ValidationError(_("Distribution %s does not exist.") % distro_name)

    def _get_signing_service(self, request):
        try:
            return SigningService.objects.get(name=request.data["signing_service"])
        except KeyError:
            raise ValidationError(_("signing_service field is required."))
        except ObjectDoesNotExist:
            raise ValidationError(
                _('Signing service "%s" does not exist.') % request.data["signing_service"]
            )
