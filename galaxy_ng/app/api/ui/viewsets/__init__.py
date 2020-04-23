from .namespace import NamespaceViewSet, MyNamespaceViewSet
from .collection import CollectionViewSet, CollectionVersionViewSet, CollectionImportViewSet
from .tags import TagsViewSet
from .current_user import CurrentUserViewSet
from .user import UserViewSet

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
