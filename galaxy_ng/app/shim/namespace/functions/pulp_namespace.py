from django.db import transaction
from django.db.models import Q
from pulp_ansible.app.models import Collection
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from galaxy_ng.app import models
from galaxy_ng.app.api.v3 import serializers
from galaxy_ng.app.exceptions import ConflictError


def create_namespace(**options) -> Response:
    """
    Create a validated namespace and return a Response object.

    This function replicates the behavior of NamespaceViewSet.create() but can be
    called independently without a request/viewset context.

    Args:
        **options: Keyword arguments containing namespace data (name, company, email, etc.)
                   and optionally a 'request' key with the Request object

    Returns:
        rest_framework.response.Response object with created namespace data

    Raises:
        ConflictError: If namespace with given name already exists
        ValidationError: If data fails serializer validation
    """
    # Extract request from options if provided
    request = options.pop('request', None)

    # Check for duplicate namespace name (409 instead of 400)
    name = options.get('name')
    if name and models.Namespace.objects.filter(name=name).exists():
        raise ConflictError(
            detail={'name': f'A namespace named {name} already exists.'}
        )

    # Validate and create namespace
    with transaction.atomic():
        context = {'request': request} if request else {}
        serializer = serializers.NamespaceSerializer(data=options, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = {}  # ViewSet would populate this with detail URL
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


def retrieve_namespace(name: str, request=None) -> Response:
    """
    Retrieve a namespace by name and return a Response object.

    Args:
        name: The name of the namespace to retrieve
        request: Optional Request object for serializer context

    Returns:
        rest_framework.response.Response object with namespace data

    Raises:
        ValidationError: If namespace does not exist
    """
    try:
        namespace = models.Namespace.objects.get(name=name)
    except models.Namespace.DoesNotExist:
        raise ValidationError(
            detail={'name': f'Namespace {name} does not exist.'}
        )

    context = {'request': request} if request else {}
    serializer = serializers.NamespaceSerializer(namespace, context=context)
    return Response(serializer.data, status=status.HTTP_200_OK)


def update_namespace(name: str, **options) -> Response:
    """
    Update a namespace and return a Response object.

    This function replicates the behavior of NamespaceViewSet.update() but can be
    called independently without a request/viewset context.

    Args:
        name: The name of the namespace to update
        **options: Keyword arguments containing fields to update (company, email, etc.)
                   and optionally a 'request' key with the Request object

    Returns:
        rest_framework.response.Response object with updated namespace data

    Raises:
        ValidationError: If namespace does not exist or data fails validation
    """
    # Extract request from options if provided
    request = options.pop('request', None)

    try:
        namespace = models.Namespace.objects.get(name=name)
    except models.Namespace.DoesNotExist:
        raise ValidationError(
            detail={'name': f'Namespace {name} does not exist.'}
        )

    with transaction.atomic():
        context = {'request': request} if request else {}
        serializer = serializers.NamespaceSerializer(
            namespace, data=options, partial=True, context=context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


def delete_namespace(name: str) -> Response:
    """
    Delete a namespace and return a Response object.

    This function replicates the behavior of NamespaceViewSet.destroy() but can be
    called independently without a request/viewset context.

    Performs checks to ensure:
    1. Namespace exists
    2. No collections are associated with the namespace

    Args:
        name: The name of the namespace to delete

    Returns:
        rest_framework.response.Response object with 204 status

    Raises:
        ValidationError: If namespace does not exist or has associated collections
    """
    try:
        namespace = models.Namespace.objects.get(name=name)
    except models.Namespace.DoesNotExist:
        raise ValidationError(
            detail={'name': f'Namespace {name} does not exist.'}
        )

    # Check if there are any collections in the namespace
    if Collection.objects.filter(namespace=namespace.name).exists():
        raise ValidationError(
            detail=(
                f"Namespace {namespace.name} cannot be deleted because "
                "there are still collections associated with it."
            )
        )

    with transaction.atomic():
        namespace.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


def list_namespaces(**filters) -> Response:
    """
    List namespaces with optional filtering and return a Response object.

    Args:
        **filters: Optional keyword arguments for filtering:
            - name: Filter by exact name
            - company: Filter by exact company
            - keywords: List of keywords to search in name/company
            - request: Optional Request object for serializer context

    Returns:
        rest_framework.response.Response object with list of namespace data
    """
    # Extract request from filters if provided
    request = filters.pop('request', None)

    queryset = models.Namespace.objects.all()

    # Apply filters
    if 'name' in filters:
        queryset = queryset.filter(name=filters['name'])
    if 'company' in filters:
        queryset = queryset.filter(company=filters['company'])
    if 'keywords' in filters:
        keywords = (
            filters['keywords'] if isinstance(filters['keywords'], list)
            else [filters['keywords']]
        )
        for keyword in keywords:
            queryset = queryset.filter(
                Q(name__icontains=keyword) | Q(company__icontains=keyword)
            )

    context = {'request': request} if request else {}
    serializer = serializers.NamespaceSummarySerializer(
        queryset, many=True, context=context
    )
    return Response(serializer.data, status=status.HTTP_200_OK)
