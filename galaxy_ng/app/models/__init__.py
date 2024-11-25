from .aiindex import AIIndexDenyList
from .auth import Group, User
from .collectionimport import CollectionImport
from .config import Setting
from .container import (
    ContainerDistribution,
    ContainerDistroReadme,
    ContainerNamespace,
    ContainerRegistryRemote,
    ContainerRegistryRepos,
)
from .namespace import Namespace, NamespaceLink
from .organization import Organization, Team
from .synclist import SyncList

from pulp_ansible.app.models import (
    AnsibleRepository,
    Collection,
    CollectionRemote,
)

from ansible_base.rbac import permission_registry

__all__ = (
    # aiindex
    "AIIndexDenyList",
    # collectionimport
    "CollectionImport",
    # container
    "ContainerDistribution",
    "ContainerDistroReadme",
    "ContainerNamespace",
    "ContainerRegistryRemote",
    "ContainerRegistryRepos",
    # auth
    "Group",
    # namespace
    "Namespace",
    "NamespaceLink",
    # organization
    "Organization",
    # config
    "Setting",
    # synclist
    "SyncList",
    "Team",
    "User",
)

permission_registry.register(
    AnsibleRepository,
    Collection,
    CollectionRemote,
    ContainerRegistryRemote,
    Namespace,
    Organization,
    Team,
    parent_field_name=None
)

permission_registry.register(
    CollectionImport, parent_field_name='namespace'
)
