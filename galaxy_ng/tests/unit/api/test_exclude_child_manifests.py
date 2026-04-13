"""
Tests for exclude_child_manifests filter scoped to the current repository
version, not global.

When a manifest exists in two repos (e.g. a push repo and a synced remote repo),
and the remote repo has a manifest list referencing it as a child, the
exclude_child_manifests filter was hiding the manifest in BOTH repos — even
though only the remote repo has the manifest list.
"""

from unittest import mock

from django.test import TestCase

from pulp_container.app import models as container_models
from pulp_container.constants import MEDIA_TYPE

from galaxy_ng.app.api.v3.viewsets.execution_environments import ManifestFilter
from galaxy_ng.app.signals.handlers import dab_rbac_signals, pulp_rbac_signals


def _create_manifest(digest, media_type=MEDIA_TYPE.MANIFEST_V2):
    return container_models.Manifest.objects.create(
        digest=digest,
        schema_version=2,
        media_type=media_type,
    )


def _create_repo_with_content(name, manifests):
    """Create a ContainerPushRepository + ContainerDistribution with the given manifests."""
    with mock.patch(
        "pulpcore.app.models.access_policy.AutoAddObjPermsMixin.add_perms"
    ), pulp_rbac_signals(), dab_rbac_signals():
        namespace = container_models.ContainerNamespace.objects.create(name=name)
        repo = container_models.ContainerPushRepository.objects.create(name=name)
        container_models.ContainerDistribution.objects.create(
            name=name,
            base_path=name,
            repository=repo,
            namespace=namespace,
        )

    with repo.new_version() as new_version:
        new_version.add_content(
            container_models.Manifest.objects.filter(pk__in=[m.pk for m in manifests])
        )

    return repo


def _get_filtered_manifests(repo):
    """Apply the exclude_child_manifests filter scoped to the repo's latest version."""
    queryset = repo.latest_version().get_content(container_models.Manifest.objects)
    return ManifestFilter(
        data={"exclude_child_manifests": "true"},
        queryset=queryset,
    ).qs


class TestExcludeChildManifestsFilter(TestCase):
    """Test that exclude_child_manifests is scoped to the current repo version."""

    def setUp(self):
        self.child_manifest = _create_manifest("sha256:child_aaa")

        self.manifest_list = _create_manifest(
            "sha256:list_bbb",
            media_type=MEDIA_TYPE.MANIFEST_LIST,
        )

        container_models.ManifestListManifest.objects.create(
            image_manifest=self.manifest_list,
            manifest_list=self.child_manifest,
        )

        # Repo A: push repo — only has the child manifest (no manifest list)
        self.repo_a = _create_repo_with_content(
            "ee-minimal-rhel8",
            [self.child_manifest],
        )

        # Repo B: synced remote repo — has both the manifest list and child
        self.repo_b = _create_repo_with_content(
            "remote/ee-minimal-rhel8",
            [self.manifest_list, self.child_manifest],
        )

    def test_manifest_visible_when_parent_not_in_repo(self):
        """Manifest is shown when its parent manifest list is in a different repo."""
        filtered = _get_filtered_manifests(self.repo_a)
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().digest, "sha256:child_aaa")

    def test_child_excluded_when_parent_in_same_repo(self):
        """Child manifest is excluded when the parent manifest list IS in the same repo."""
        filtered = _get_filtered_manifests(self.repo_b)
        # Only the manifest list should remain
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().digest, "sha256:list_bbb")

    def test_standalone_manifest_not_excluded(self):
        """A manifest with no parent links is never excluded."""
        standalone = _create_manifest("sha256:standalone_ccc")
        repo = _create_repo_with_content("standalone-repo", [standalone])

        filtered = _get_filtered_manifests(repo)
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().digest, "sha256:standalone_ccc")
