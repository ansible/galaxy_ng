"""Django Models for Dynamic Settings Managed by Dynaconf.

Functionality:
    - Create a new Setting entry, keeping the latest 10 versions in DB
    - A Setting model stores key:value for Dynaconf
    - Validators are set on dynamic_settings.py:DYNAMIC_SETTINGS_SCHEMA
    - Only keys defined in DYNAMIC_SETTINGS_SCHEMA can be set in DB
    - Before saving there is a validation that checks if key:value is valid
    - Values are strings parsed by Dynaconf (all dynaconf merging/markers are supported)
    - The value must be accessed through Dynaconf or Setting.get method
    - Creating or deleting will update the Redis Cache when redis is available

Setting a new value in the database:
    # Only keys defined in DYNAMIC_SETTINGS_SCHEMA can be set in DB

    Setting.set_value_in_db("FOO", "bar")  # accepts optional `user`
    Setting.set_value_in_db("MY_PATH", "@format {this.BASE_PATH}/foo/bar")
    Setting.set_value_in_db("MY_LIST", "@merge [1, 2, 3]")
    Setting.set_value_in_db("DATA__key__nested", "thing")
    Setting.set_secret_in_db("TOKEN", "123456")
    # Setting a secret only mark it as a secret, making it read only on the API.

Reading a RAW value directly from database: (not recommended)
    # This will not be parsed by Dynaconf

    Setting.get_setting_from_db("FOO") -> <Setting: FOO='bar' [v-1]>
    Setting.get_value_from_db("MY_PATH") -> "@format {this.BASE_PATH}/foo/bar"
    Setting.get_all() -> [<Setting: FOO='bar' [v-1]>, <Setting: MY_PATH='...' [v-1]>]
    Setting.as_dict() -> {"FOO": "bar", "MY_PATH": "@format {this.BASE_PATH}/foo/bar"}

Reading a value parsed by Dynaconf:

    Setting.get("PATH") -> "/base_path/to/foo/bar")

    # The above is the equivalent of reading the value directly from dynaconf
    # via dango.conf.settings, however this works only when the system has
    # GALAXY_DYNAMIC_SETTINGS enabled.
    from django.conf import settings
    settings.PATH -> "/base_path/to/foo/bar"  # this triggers the lookup on database/cache

Updating Cache:

    # When Redis connection is available the cache will be created/updated
    # on every call to methods that writes to database.
    # However if you want to force a cache update you can call:

    Setting.update_cache()

"""

import logging
import time

from dynaconf import Validator
from dynaconf.utils import upperfy
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django_lifecycle import (
    AFTER_CREATE,
    AFTER_DELETE,
    BEFORE_CREATE,
    LifecycleModelMixin,
    hook
)

from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA

logger = logging.getLogger(__name__)

setting_key_validator = RegexValidator(
    r"^(?!\d)[a-zA-Z0-9_]+$",
    "alphanumeric, no spaces, no hyphen, only underscore cant start with a number.",
)

MAX_VERSIONS_TO_KEEP = 10
empty = object()
__all__ = ["Setting"]


class SettingsManager(models.Manager):
    def create(self, key, value, *args, **kwargs):
        """Creates a new Setting entry, keeping the latest versions in DB
        uses a lock to ensure no version bump collisions.

        If Redis is not available, skip locking and just create the new entry.
        """
        key = upperfy(key)  # Key first level must be uppercase

        from galaxy_ng.app.tasks.settings_cache import acquire_lock, release_lock  # noqa

        for __ in range(10):  # try 10 times
            lock = acquire_lock(key)
            if lock is not None:
                break
            time.sleep(.5)  # blocking

        if lock is None:
            raise Exception("Could not acquire lock for key")

        existing = self.get_queryset().filter(key=key)
        if existing:
            kwargs["version"] = existing.latest("version").version + 1

        new = super().create(key=key, value=value, *args, **kwargs)

        release_lock(key, lock)

        # Delete old versions
        self.get_queryset().filter(
            key=key,
            version__lt=new.version - MAX_VERSIONS_TO_KEEP
        ).delete()

        return new

    def filter(self, *args, **kwargs):
        """case insensitive filter"""
        if "key" in kwargs:
            kwargs["key__iexact"] = kwargs.pop("key")
        return super().filter(*args, **kwargs)


class Setting(LifecycleModelMixin, models.Model):
    """Setting model stores key:value for Dynaconf.

    The recommended usage is via custom methods.

    Setting.set_value_in_db('FOO__BAR', 'baz')
    Setting.get_value_from_db('FOO__BAR') -> 'baz'
    Setting.as_dict() -> {'FOO__BAR': 'baz'}
    Setting.get_all() -> [
        Setting(key='FOO__BAR', value='baz', user=None, version=1, is_secret=False, created_at=...)
    ]
    """
    objects = SettingsManager()

    key = models.CharField(
        max_length=255,
        null=False,
        validators=[setting_key_validator],
    )
    value = models.TextField(blank=False, null=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        editable=False,
        default=None,
        related_name="settings",
    )
    version = models.IntegerField(default=1, null=False)
    is_secret = models.BooleanField(default=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def update_cache(cls):
        from galaxy_ng.app.tasks.settings_cache import update_setting_cache  # noqa

        update_setting_cache(cls.as_dict())

    @hook(AFTER_CREATE, on_commit=True)
    def _hook_update_create(self):
        """After create update the whole cache"""
        self.update_cache()
        logger.debug(
            "Settings cache updated - create - %s[%s]:%s", self.key, self.version, self.value
        )

    @hook(AFTER_DELETE, on_commit=True)
    def _hook_delete_cache(self):
        self.update_cache()
        logger.debug(
            "Settings cache updated delete - %s[%s]:%s", self.key, self.version, self.value
        )

    @hook(BEFORE_CREATE)
    def _hook_validate(self):
        """Validate and transform before creation.

        1. Fix the True/False problem:
            Dynaconf only parses as boolean if values are lowercase true/false
            or explicitly marked with @bool
            So if value is True or False, we transform to lowercase.
            OR stringify value
        2. Validate against Dynacic Settings Schema
        3. Validate against Dynaconf Validators
        """
        self.value = (
            str(self.value).lower() if str(self.value) in ["True", "False"] else str(self.value)
        )

        if self.base_key not in DYNAMIC_SETTINGS_SCHEMA:
            raise Exception(f"Setting {self.key} not allowed by schema")

        logger.debug("validate %s via settings validators", self.key)
        current_db_data = self.as_dict()
        validator = DYNAMIC_SETTINGS_SCHEMA[self.base_key].get("validator", Validator())
        validator.names = [self.base_key]
        temp_settings = settings.dynaconf_clone()
        temp_settings.validators.register(validator)
        temp_settings.update(current_db_data, tomlfy=True)
        temp_settings.set(self.key, self.value, tomlfy=True)
        temp_settings.validators.validate()

    @classmethod
    def get(cls, key, default=empty):
        """Get a setting value directly from database.
        but parsing though Dynaconf before returning.
        """
        current_db_data = cls.as_dict()
        temp_settings = settings.dynaconf_clone()
        temp_settings.update(current_db_data, tomlfy=True)
        value = temp_settings.get(key, default)
        if value is empty:
            raise KeyError(f"Setting {key} not found in database")
        return value

    @property
    def base_key(self):
        """Return the base key 'FOO__BAR' -> 'FOO'"""
        return self.key.split("__")[0].upper()

    @property
    def display_value(self):
        return f"{self.value[:3]}***" if self.is_secret else self.value

    @classmethod
    def get_value_from_db(cls, key):
        return cls.get_setting_from_db(key).value

    @classmethod
    def get_setting_from_db(cls, key):
        return cls.objects.filter(key=key).latest("version")

    @classmethod
    def get_all(cls):
        return (
            cls.objects.annotate(key_lower=Lower("key"))
            .order_by("key_lower", "-version")
            .distinct("key_lower")
        )

    @classmethod
    def as_dict(cls):
        return {s.key: s.value for s in cls.get_all()}

    @classmethod
    @transaction.atomic
    def set_value_in_db(cls, key, value, user=None, is_secret=False):
        return cls.objects.create(key=key, value=value, user=user, is_secret=is_secret)

    @classmethod
    def set_secret_in_db(cls, key, value, user=None):
        return cls.set_value_in_db(key, value, user, is_secret=True)

    @classmethod
    @transaction.atomic
    def delete_latest_version(cls, key):
        result = cls.objects.filter(key=key).latest("version").delete()
        cls.update_cache()
        return result

    @classmethod
    @transaction.atomic
    def delete_all_versions(cls, key):
        result = cls.objects.filter(key=key).delete()
        cls.update_cache()
        return result

    def __str__(self):
        return f"{self.key}={self.display_value!r} [v-{self.version}]"

    class Meta:
        permissions = (("edit_setting", "Can edit setting"),)
        unique_together = ("key", "version")
