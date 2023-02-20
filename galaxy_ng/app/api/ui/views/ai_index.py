from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError


from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.models.aiindex import AIIndexDenyList
from galaxy_ng.app.models.namespace import Namespace

NamespaceOrLegacyNamespace = (
    access_policy.NamespaceAccessPolicy | access_policy.LegacyAccessPolicy
)  # DRF 3+ allows composed access policies using & or |


class AIDenyIndexBaseView(api_base.APIView):
    permission_classes = [NamespaceOrLegacyNamespace]

    def get_object(self):
        """Pulp requires this method even when not used,e.g: Not a Model ViewSet"""

    def _verify_permission_for_namespace_object(self, request, scope, reference):
        """Checks if the user has permission to modify the namespace object."""

        model = {"namespace": Namespace, "legacy_namespace": LegacyNamespace}
        try:
            namespace = model[scope].objects.get(name=reference)
        except ObjectDoesNotExist:
            raise DRFValidationError(f"Referenced {scope} {reference!r} does not exist")
        except KeyError:
            raise DRFValidationError(f"Invalid scope {scope!r}")

        # This is a method on DRF that will use permission_classes to check
        # for object permissions, because this is not a ModelViewSet, this method
        # must be called manually.
        self.check_object_permissions(request, namespace)  # will raise permission error


class AIDenyIndexAddView(AIDenyIndexBaseView):
    """Allows to add a namespace to AIIndexDenyList."""
    action = "ai-deny-index-add"

    @extend_schema(
        request=inline_serializer(
            name="AddToAIIndexDenyList",
            fields={"reference": serializers.CharField()}
        ),
        parameters=[
            OpenApiParameter(
                "scope", OpenApiTypes.STR, "path", enum=["namespace", "legacy_namespace"]
            )
        ],
        responses={
            201: inline_serializer(
                name="AddedToAIIndexDenyList",
                fields={"scope": serializers.CharField, "reference": serializers.CharField},
            ),
            403: "Forbidden",
            400: "Bad Request",
            409: "Conflict"
        },
    )
    @transaction.atomic
    def post(self, request, scope, *args, **kwargs):
        """Adds a collection to the AI Index deny list.

        http::
            POST _ui/v1/ai_deny_index/{namespace|legacy_namespace}/
            {
                "reference": "some_name"
            }

        responses:
            201: Created
            400: Bad Request (invalid payload data)
            409: Conflict (data already in the model)
        """
        data = {"scope": scope, "reference": request.data.get("reference")}
        obj = AIIndexDenyList(**data)
        # For now it will not cast the entry across name matching
        # namespaces and legacy namespaces.
        try:
            obj.full_clean(validate_unique=False)
        except ValidationError as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)

        self._verify_permission_for_namespace_object(request, **data)

        try:
            obj.save()
        except IntegrityError as e:
            return Response(str(e), status=status.HTTP_409_CONFLICT)

        return Response(
            {"scope": obj.scope, "reference": obj.reference},
            status=status.HTTP_201_CREATED
        )


class AIDenyIndexListView(AIDenyIndexBaseView):
    """Lists all entries in the AIIndexDenyList.
    Open without auth.
    """
    action = "ai-deny-index-list"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="AIIndexDenyResults",
                fields={
                    "results": serializers.ListField(
                        child=inline_serializer(
                            name="AIIndexDenyList",
                            fields={
                                "scope": serializers.CharField(),
                                "reference": serializers.CharField(),
                            }
                        )
                    ),
                    "count": serializers.IntegerField(),
                }
            )
        },
        parameters=[
            OpenApiParameter(
                "scope",
                OpenApiTypes.STR,
                enum=["namespace", "legacy_namespace"],
                description="Filter by scope",
            ),
            OpenApiParameter(
                "reference",
                OpenApiTypes.STR,
                description="Filter by reference (namespace name)",
            ),
        ]
    )
    def get(self, request, *args, **kwargs):
        """Returns a list of all entries in the AI Index deny list.

        http::
            GET _ui/v1/ai_deny_index/
            GET _ui/v1/ai_deny_index/?scope=namespace

        responses:
            200: Ok {"results": ["..."], "count": 1}

        Query params:
            scope: "namespace" or "legacy_namespace" to filter
            reference: filter by reference (namespace name)

        Sorted by reference field.
        """
        qs = AIIndexDenyList.objects.all().order_by("reference")
        if scope := request.GET.get("scope"):
            qs = qs.filter(scope__iexact=scope)
        if reference := request.GET.get("reference"):
            qs = qs.filter(reference__iexact=reference)
        return Response(
            {
                "results": [
                    {"scope": item.scope, "reference": item.reference}
                    for item in qs
                ],
                "count": qs.count(),
            }
        )


class AIDenyIndexDetailView(AIDenyIndexBaseView):
    """Access specific AIIndexDenyList Object and allow deletion."""
    action = "ai-deny-index-delete"

    @extend_schema(
        responses={
            204: "No Content (deleted)",
            403: "Forbidden",
            404: "Not Found",
        },
        parameters=[
            OpenApiParameter(
                "scope", OpenApiTypes.STR, "path", enum=["namespace", "legacy_namespace"]
            )
        ],
    )
    @transaction.atomic
    def delete(self, request, scope, reference, *args, **kwargs):
        """Deletes an entry from the AI Index deny list.

        http::
            DELETE _ui/v1/ai_deny_index/{scope}/{reference}/

        responses:
            204: No content (deleted)
            403: Forbidden
            404: Item for deletion not found
        """
        try:
            obj = AIIndexDenyList.objects.get(scope=scope, reference=reference)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self._verify_permission_for_namespace_object(request, scope, reference)

        obj.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
