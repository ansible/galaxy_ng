from unittest.mock import patch

from django.test import TestCase
from pulp_ansible.app.models import AnsibleRepository, Collection

from django.conf import settings
from galaxy_ng.app.api.resource_api import RESOURCE_LIST
from galaxy_ng.app.models import Namespace, Setting
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA
from galaxy_ng.app.models.config import MAX_VERSIONS_TO_KEEP

DYNAMIC_SETTINGS_SCHEMA["TEST"] = {}
DYNAMIC_SETTINGS_SCHEMA["FOO"] = {}


class TestSignalCreateRepository(TestCase):
    def test_create_repository_ensure_retain_repo_versions(self):
        """On creation retain_repo_versions is set to 1 if omited"""
        repo_name = "test"
        repository = AnsibleRepository.objects.create(name=repo_name)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 1)

    def test_when_set_not_changed_retain_repo_versions(self):
        """On creation retain_repo_versions is not changed when explicit set"""
        repo_name = "test2"
        repository = AnsibleRepository.objects.create(name=repo_name, retain_repo_versions=99)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 99)

    def test_update_do_not_change_retain_repo_versions(self):
        """On update retain_repo_versions is not changed when already exists"""
        # Create repo setting retain_repo_versions
        repo_name = "test3"
        repository = AnsibleRepository.objects.create(name=repo_name, retain_repo_versions=99)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 99)
        # Update the name of the repo
        AnsibleRepository.objects.filter(pk=repository.pk).update(name="test3_2")
        updated = AnsibleRepository.objects.get(pk=repository.pk)
        # Ensure name changed but retain_repo_versions did not
        self.assertEqual(updated.name, "test3_2")
        self.assertEqual(updated.retain_repo_versions, 99)


class TestNamespaceResourceSync(TestCase):
    def test_skip_reverse_resource_sync_flag_is_set(self):
        """Namespace must opt out of ansible_base's reverse sync post-save signal.

        Namespace is registered in the resource registry for UUID generation only.
        Gateway has no handler for galaxy.namespace, so pushing namespace data
        upstream would crash with TypeError (serializer_class is None) and roll
        back the transaction, returning HTTP 500 on every namespace save.
        """
        self.assertTrue(
            getattr(Namespace, "_skip_reverse_resource_sync", False),
            "_skip_reverse_resource_sync must be True on Namespace to prevent the "
            "reverse sync signal from crashing when RESOURCE_SERVER_SYNC_ENABLED=True",
        )

    def test_unmanaged_resource_types_skip_reverse_sync(self):
        """Any model registered without a managed_serializer must opt out of reverse sync.

        When RESOURCE_SERVER_SYNC_ENABLED=True, ansible_base connects a post_save
        signal that calls resource_type.serializer_class(instance) for all registered
        models. For resource types with no managed_serializer, serializer_class is None
        and the call raises TypeError, rolling back the transaction and returning 500.

        Any ResourceConfig added to RESOURCE_LIST without a shared_resource (and
        therefore no managed_serializer) must set _skip_reverse_resource_sync = True
        on the model to prevent this.
        """
        unmanaged = [config for config in RESOURCE_LIST if config.managed_serializer is None]
        missing_flag = [
            config.model.__name__
            for config in unmanaged
            if not getattr(config.model, "_skip_reverse_resource_sync", False)
        ]
        self.assertEqual(
            missing_flag,
            [],
            f"These models are registered in RESOURCE_LIST without a managed_serializer "
            f"but are missing _skip_reverse_resource_sync = True: {missing_flag}. "
            f"Add the flag to prevent TypeError in ansible_base's reverse sync signal "
            f"when RESOURCE_SERVER_SYNC_ENABLED=True.",
        )

    def test_namespace_create_succeeds_when_reverse_sync_enabled(self):
        """Namespace.save() must not raise when reverse sync is enabled.

        Simulates the OCP+Gateway environment where _should_reverse_sync() returns
        True. Without _skip_reverse_resource_sync=True, ansible_base's post-save
        signal calls resource_type.serializer_class(instance) which is None for
        Namespace, raising TypeError and causing HTTP 500.
        """
        with patch("ansible_base.resource_registry.apps._should_reverse_sync", return_value=True):
            # Should not raise — _skip_reverse_resource_sync=True causes
            # should_skip_reverse_sync() to return True before serializer_class is called
            ns = Namespace.objects.create(name="test_sync_skip")

        self.assertTrue(Namespace.objects.filter(name="test_sync_skip").exists())
        ns.delete()


class TestSignalCreateNamespace(TestCase):
    namespace_name = "my_test_ns"

    def test_new_collection_create_namespace(self):
        self.assertFalse(Namespace.objects.filter(name=self.namespace_name))
        Collection.objects.create(
            name="my_collection",
            namespace=self.namespace_name,
        )
        self.assertTrue(Namespace.objects.filter(name=self.namespace_name))

    def test_existing_namespace_not_changed(self):
        description = "Namespace created not by signal"
        Namespace.objects.create(
            name=self.namespace_name,
            description=description,
        )
        Collection.objects.create(
            name="my_collection",
            namespace=self.namespace_name,
        )
        namespace = Namespace.objects.get(name=self.namespace_name)
        self.assertEqual(namespace.description, description)


class TestSetting(TestCase):
    def setUp(self):
        """Ensure Table is clean before each case"""
        Setting.objects.all().delete()

    def test_create_setting_directly(self):
        Setting.objects.create(key="test", value="value")

        # Lowercase read
        setting = Setting.get_setting_from_db("test")
        self.assertEqual(setting.key, "TEST")
        self.assertEqual(setting.value, "value")

        # Uppercase read
        setting = Setting.get_setting_from_db("TEST")
        self.assertEqual(setting.key, "TEST")
        self.assertEqual(setting.value, "value")

        # Bump the version
        first_version = setting.version
        Setting.objects.create(key="test", value="value2")
        setting = Setting.get_setting_from_db("test")
        self.assertEqual(setting.key, "TEST")
        self.assertEqual(setting.value, "value2")
        assert setting.version > first_version

    def test_only_latest_x_old_versions_are_kept(self):
        for i in range(MAX_VERSIONS_TO_KEEP * 2):
            Setting.objects.create(key="test", value=f"value{i}")

        assert Setting.objects.filter(key="test").count() == MAX_VERSIONS_TO_KEEP + 1

    def test_get_settings_as_dict(self):
        Setting.set_value_in_db("FOO", "BAR")
        Setting.set_value_in_db("TEST", 1)
        assert Setting.as_dict() == {"FOO": "BAR", "TEST": "1"}

    def test_get_settings_all(self):
        Setting.set_value_in_db("FOO", "BAR")
        Setting.set_value_in_db("FOO", "BAR2")
        Setting.set_value_in_db("TEST", 1)
        assert len(Setting.get_all()) == 2
        assert Setting.objects.all().count() == 3

    def test_get_setting_icase(self):
        Setting.set_value_in_db("FOO", "BAR")
        assert Setting.get_value_from_db("foo") == "BAR"
        assert Setting.get_value_from_db("FOO") == "BAR"

    def test_setting_bool_casing_fix(self):
        Setting.set_value_in_db("FOO", "True")
        assert Setting.get_value_from_db("foo") == "true"
        Setting.set_value_in_db("FOO", "False")
        assert Setting.get_value_from_db("FOO") == "false"

    def test_display_secret(self):
        Setting.set_secret_in_db("FOO", "SECRETDATA123")
        assert Setting.get_value_from_db("FOO") == "SECRETDATA123"
        assert Setting.get_setting_from_db("FOO").display_value == "SEC***"

    def test_delete_all_setting_versions(self):
        Setting.set_value_in_db("FOO", "BAR")
        Setting.set_value_in_db("FOO", "BAR2")
        Setting.delete_latest_version("FOO")
        assert Setting.get_value_from_db("FOO") == "BAR"
        Setting.delete_all_versions("FOO")
        assert Setting.objects.filter(key="FOO").count() == 0

    def test_dynaconf_parsing(self):
        Setting.set_value_in_db("FOO", "BAR")
        settings.set("FOO", "BAR")
        Setting.set_value_in_db("TEST", "@format {this.FOO}/TEST")
        assert Setting.get("TEST") == "BAR/TEST"

        Setting.set_value_in_db("FOO", "@bool 0")
        Setting.set_value_in_db("TEST", "@int 42")
        assert Setting.get("TEST") == 42
        assert Setting.get("FOO") is False

        Setting.set_value_in_db("FOO__key1", "BAR")
        Setting.set_value_in_db("FOO__key2", "BAR2")
        assert Setting.get("FOO") == {"key1": "BAR", "key2": "BAR2"}

        Setting.set_value_in_db("FOO", '@json {"colors": ["red"]}')
        Setting.set_value_in_db("FOO__colors", "@merge green,blue")
        assert Setting.get("FOO") == {
            "colors": ["red", "green", "blue"],
            "key1": "BAR",
            "key2": "BAR2",
        }
