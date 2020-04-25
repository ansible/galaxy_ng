from .namespace import NamespaceViewSet, MyNamespaceViewSet
from .collection import CollectionViewSet, CollectionVersionViewSet, CollectionImportViewSet
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
