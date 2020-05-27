from .namespace import (
    NamespaceViewSet,
)

from .collection import CollectionViewSet, CollectionVersionViewSet, CollectionImportViewSet
from .my_namespace import MyNamespaceViewSet
from .tags import TagsViewSet
from .user import UserViewSet, CurrentUserViewSet

__all__ = (
    'NamespaceViewSet',
    'MyNamespaceViewSet',
    'CollectionViewSet',
    'CollectionVersionViewSet',
    'CollectionImportViewSet',
    'TagsViewSet',
    'CurrentUserViewSet',
    'UserViewSet'
)
