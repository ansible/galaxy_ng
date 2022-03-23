from collections import OrderedDict

from django.conf import settings

from rest_framework import (
    serializers,
    viewsets,
    views,
    permissions,
    generics
)

from rest_framework.settings import perform_import


GALAXY_EXCEPTION_HANDLER = perform_import(
    settings.GALAXY_EXCEPTION_HANDLER,
    'GALAXY_EXCEPTION_HANDLER'
)
GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)
GALAXY_PAGINATION_CLASS = perform_import(
    settings.GALAXY_PAGINATION_CLASS,
    'GALAXY_PAGINATION_CLASS'
)


class _MustImplementPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        raise NotImplementedError("subclass must implement permission_classes")


class LocalSettingsMixin:
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES
    pagination_class = GALAXY_PAGINATION_CLASS
    permission_classes = [_MustImplementPermission]

    def get_exception_handler(self):
        return GALAXY_EXCEPTION_HANDLER


class APIView(LocalSettingsMixin, views.APIView):
    pass


class ViewSet(LocalSettingsMixin, viewsets.ViewSet):
    pass


class GenericAPIView(LocalSettingsMixin, generics.GenericAPIView):
    pass


class GenericViewSet(LocalSettingsMixin, viewsets.GenericViewSet):
    pass


class ModelViewSet(LocalSettingsMixin, viewsets.ModelViewSet):
    pass


class RelatedFieldsBaseSerializer(serializers.Serializer):
    """
    Serializer only returns fields specified in 'include_related' query param.

    This allows for fields that require more database queries to be optionally
    included in API responses, which lowers the load on the backend. This is
    intended as a way to include extra data in list views.

    Usage:

    This functions the same as DRF's base `serializers.Serializer` class with the
    exception that it will only return fields specified in the `?include_related=`
    query parameter.

    Example:

    MySerializer(RelatedFieldsBaseSerializer):
        foo = CharField()
        bar = CharField()

    MySerializer will return:

    {"foo": None} when called with `?include_related=foo` and {"foo": None, "bar" None}
    when called with `?include_related=foo&include_related=bar`.
    """

    def __init__(self, *args, **kwargs):
        # This should only be included as a sub serializer and shouldn't be used for
        # updating objects, so set read_only to true
        kwargs['read_only'] = True
        return super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        result = OrderedDict()
        fields = self._readable_fields
        request = self.context.get('request', None)
        if request:

            # TODO: Figure out how to make `include_related` show up in the open API spec
            include_fields = request.GET.getlist('include_related')

            if len(include_fields) > 0:
                for field in fields:
                    if field.field_name in include_fields:
                        result[field.field_name] = field.to_representation(instance)
        else:
            # When there is no request present, it usually means that the serializer is
            # being inspected by DRF spectacular to generate the open API spec. In that
            # case, this should act like a normal serializer.
            return super().to_representation(instance)

        return result
