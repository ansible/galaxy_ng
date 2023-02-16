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


class AIIndexBaseView(api_base.APIView):
    permission_classes = [NamespaceOrLegacyNamespace]

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


class AIIndexAddView(AIIndexBaseView):
    """Allows to add a namespace to AIIndexDenyList."""
    action = "ai-index-add"

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
            POST _ui/v1/ai_index/{namespace|legacy_namespace}/
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


class AIIndexListView(AIIndexBaseView):
    """Lists all entries in the AIIndexDenyList.
    Open without auth.
    """
    action = "ai-index-list"

    @extend_schema(
        responses={
            200: inline_serializer(
                name="AIIndexDenyList",
                fields={"items": serializers.ListField(child=serializers.CharField())}
            )
        },
        parameters=[
            OpenApiParameter("scope", OpenApiTypes.STR, enum=["namespace", "legacy_namespace"])
        ]
    )
    def get(self, request, *args, **kwargs):
        """Returns a list of all entries in the AI Index deny list.

        http::
            GET _ui/v1/ai_index/
            GET _ui/v1/ai_index/?scope=namespace

        responses:
            200: Ok {items: ["..."]}

        Query params:
            scope: "namespace" or "legacy_namespace" to filter

        Sorted by reference field.
        """
        qs = AIIndexDenyList.objects.all().order_by("reference")
        if scope := request.GET.get("scope"):
            qs = qs.filter(scope=scope)
        items = qs.values_list("reference", flat=True)
        return Response({"items": list(items)})


class AIIndexDetailView(AIIndexBaseView):
    """Access specific AIIndexDenyList Object and allow deletion."""
    action = "ai-index-delete"

    @extend_schema(
        responses={
            200: "Ok (deleted)",
            204: "No Content (not found)",
            403: "Forbidden"
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
            DELETE _ui/v1/ai_index/{scope}/{reference}/

        responses:
            200: Ok (deleted)
            204: No Content (not found)
        """
        try:
            obj = AIIndexDenyList.objects.get(scope=scope, reference=reference)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

        self._verify_permission_for_namespace_object(request, scope, reference)

        obj.delete()

        return Response(status=status.HTTP_200_OK)
