import uuid

import pytest

from pulpcore.app.models import Task
from pulpcore.constants import TASK_STATES

from galaxy_ng.app.api.v1.filtersets import LegacyRoleImportFilter
from galaxy_ng.app.api.v1.models import LegacyNamespace, LegacyRole, LegacyRoleImport
from galaxy_ng.app.models import Namespace


def _create_import(github_user, github_repo, state=TASK_STATES.COMPLETED, role=None):
    task = Task.objects.create(
        name="galaxy_ng.app.api.v1.tasks.legacy_role_import",
        state=state,
        logging_cid=str(uuid.uuid4()),
        enc_kwargs={
            "github_user": github_user,
            "github_repo": github_repo,
            "request_username": "admin",
        },
    )
    return LegacyRoleImport.objects.create(task=task, role=role, messages=[])


def _create_namespace(name):
    v3_ns, _ = Namespace.objects.get_or_create(name=name)
    legacy_ns, _ = LegacyNamespace.objects.get_or_create(name=name)
    legacy_ns.namespace = v3_ns
    legacy_ns.save()
    return legacy_ns


def _create_role(namespace, name, github_user, github_repo):
    return LegacyRole.objects.create(
        namespace=namespace,
        name=name,
        full_metadata={
            "github_user": github_user,
            "github_repo": github_repo,
        },
    )


@pytest.fixture
def import_data():
    ns_alice = _create_namespace("alice")
    ns_bob = _create_namespace("bob")

    role_alice_web = _create_role(ns_alice, "web", "alice", "ansible-role-web")
    role_bob_db = _create_role(ns_bob, "db", "bob", "ansible-role-db")

    imp_alice_1 = _create_import("alice", "ansible-role-web", role=role_alice_web)
    imp_alice_2 = _create_import("alice", "ansible-role-web", role=role_alice_web)
    imp_bob = _create_import("bob", "ansible-role-db", role=role_bob_db)
    imp_orphan = _create_import("alice", "ansible-role-web", state=TASK_STATES.FAILED)

    return {
        "imp_alice_1": imp_alice_1,
        "imp_alice_2": imp_alice_2,
        "imp_bob": imp_bob,
        "imp_orphan": imp_orphan,
    }


@pytest.mark.django_db
class TestLegacyRoleImportFilterGithubUser:

    def test_filters_by_github_user(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"github_user": "alice"}, queryset=qs)
        results = list(f.qs)

        assert import_data["imp_alice_1"] in results
        assert import_data["imp_alice_2"] in results
        assert import_data["imp_orphan"] in results
        assert import_data["imp_bob"] not in results

    def test_no_match_returns_empty(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"github_user": "nobody"}, queryset=qs)
        assert f.qs.count() == 0

    def test_includes_orphan_imports(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"github_user": "alice"}, queryset=qs)
        results = list(f.qs)
        assert import_data["imp_orphan"] in results


@pytest.mark.django_db
class TestLegacyRoleImportFilterGithubRepo:

    def test_filters_by_github_repo(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"github_repo": "ansible-role-web"}, queryset=qs)
        results = list(f.qs)

        assert import_data["imp_alice_1"] in results
        assert import_data["imp_alice_2"] in results
        assert import_data["imp_orphan"] in results
        assert import_data["imp_bob"] not in results

    def test_no_match_returns_empty(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"github_repo": "nonexistent"}, queryset=qs)
        assert f.qs.count() == 0


@pytest.mark.django_db
class TestLegacyRoleImportFilterCombined:

    def test_both_filters(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter(
            {"github_user": "alice", "github_repo": "ansible-role-web"}, queryset=qs
        )
        results = list(f.qs)

        assert import_data["imp_alice_1"] in results
        assert import_data["imp_alice_2"] in results
        assert import_data["imp_orphan"] in results
        assert import_data["imp_bob"] not in results

    def test_mismatched_user_and_repo(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter(
            {"github_user": "alice", "github_repo": "ansible-role-db"}, queryset=qs
        )
        assert f.qs.count() == 0


@pytest.mark.django_db
class TestLegacyRoleImportFilterState:

    def test_filter_by_completed(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"state": "completed"}, queryset=qs)
        results = list(f.qs)

        assert import_data["imp_alice_1"] in results
        assert import_data["imp_alice_2"] in results
        assert import_data["imp_bob"] in results
        assert import_data["imp_orphan"] not in results

    def test_success_maps_to_completed(self, import_data):
        qs = LegacyRoleImport.objects.all()
        completed = LegacyRoleImportFilter({"state": "completed"}, queryset=qs)
        success = LegacyRoleImportFilter({"state": "success"}, queryset=qs)
        assert list(completed.qs) == list(success.qs)

    def test_filter_by_failed(self, import_data):
        qs = LegacyRoleImport.objects.all()
        f = LegacyRoleImportFilter({"state": "failed"}, queryset=qs)
        results = list(f.qs)

        assert import_data["imp_orphan"] in results
        assert len(results) == 1
