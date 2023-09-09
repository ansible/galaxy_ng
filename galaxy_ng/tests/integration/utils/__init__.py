"""Utility functions for AH tests."""

from .client_ansible_lib import get_client
from .client_ansible_galaxy_cli import ansible_galaxy
from .client_social_github import SocialGithubClient
from .client_ui import UIClient
from .collection_inspector import CollectionInspector
from .collections import (
    build_collection,
    copy_collection_version,
    delete_all_collections,
    upload_artifact,
    modify_artifact,
    get_collections_namespace_path,
    get_collection_full_path,
    set_certification,
    get_all_collections_by_repo,
    get_all_repository_collection_versions,
)
from .errors import (
    TaskWaitingTimeout,
    CapturingGalaxyError,
)
from .namespaces import (
    generate_namespace,
    get_all_namespaces,
    generate_unused_namespace,
    create_unused_namespace,
    cleanup_namespace
)
from .tasks import wait_for_task, wait_for_task_ui_client, wait_for_all_tasks
from .tools import is_docker_installed, uuid4, iterate_all, gen_string

from .urls import (
    url_safe_join,
    wait_for_url
)
from .users import (
    delete_group,
    create_user,
    delete_user
)
from .sync import (
    set_synclist,
    clear_certified,
    perform_sync,
)
from .pulp_interfaces import AnsibleDistroAndRepo, PulpObjectBase
from .signatures import create_local_signature_for_tarball
from .github import GithubAdminClient


__all__ = (
    get_client,
    ansible_galaxy,
    copy_collection_version,
    create_local_signature_for_tarball,
    SocialGithubClient,
    UIClient,
    CollectionInspector,
    build_collection,
    upload_artifact,
    modify_artifact,
    get_collections_namespace_path,
    get_collection_full_path,
    set_certification,
    get_all_collections_by_repo,
    get_all_repository_collection_versions,
    TaskWaitingTimeout,
    CapturingGalaxyError,
    generate_namespace,
    get_all_namespaces,
    generate_unused_namespace,
    create_unused_namespace,
    cleanup_namespace,
    wait_for_task,
    wait_for_task_ui_client,
    is_docker_installed,
    uuid4,
    url_safe_join,
    wait_for_url,
    delete_group,
    create_user,
    delete_user,
    set_synclist,
    clear_certified,
    perform_sync,
    iterate_all,
    wait_for_all_tasks,
    gen_string,
    AnsibleDistroAndRepo,
    delete_all_collections,
    PulpObjectBase,
    GithubAdminClient
)
