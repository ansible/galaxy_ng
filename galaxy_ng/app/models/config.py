import logging
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django_lifecycle import (AFTER_CREATE, AFTER_DELETE, BEFORE_CREATE,
                              LifecycleModelMixin, hook)
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA

logger = logging.getLogger(__name__)

__all__ = ["Setting"]


class SettingsManager(models.Manager):
    def create(self, key, value, *args, **kwargs):
        """Increase version field on create."""
        # TODO: Acquire lock (use pulp task manager? or a transaction atomic?)
        existing = self.get_queryset().filter(key=key)
        if existing:
            kwargs["version"] = existing.latest("version").version + 1
        # TODO: Validate key value pair
        new = super().create(key=key, value=value, *args, **kwargs)
        # TODO: Release lock
        # TODO: Keep only 10 latest versions
        return new

    def filter(self, *args, **kwargs):
        """case insensitive filter"""
        if "key" in kwargs:
            kwargs["key__iexact"] = kwargs.pop("key")
        return super().filter(*args, **kwargs)


setting_key_validator = RegexValidator(
    r"^(?!\d)[a-zA-Z0-9_]+$",
    "alphanumeric, no spaces, no hyphen, only underscore cant start with a number.",
)


class Setting(LifecycleModelMixin, models.Model):
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
            "Settings cache updated - create - %s[%s]:%s",
            self.key, self.version, self.value
        )

    @hook(AFTER_DELETE, on_commit=True)
    def _hook_delete_cache(self):
        self.update_cache()
        logger.debug(
            "Settings cache updated delete - %s[%s]:%s",
            self.key, self.version, self.value
        )

    @hook(BEFORE_CREATE)
    def _hook_validate(self):
        # Fix the True/False problem:
        # Dynaconf only parses as boolean if values are lowercase true/false
        # or explicitly marked with @bool
        # So if value is True or False, we transform to lowercase.
        self.value = str(self.value).lower() if str(self.value) in ["True", "False"] else str(self.value)
        logger.debug("validate %s via settings validators", self.key)
        # TODO: Create a settings copy, build a Validation from schema, validate it.

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
        return cls.objects.filter(key=key).latest("version").delete()

    @classmethod
    @transaction.atomic
    def delete_all_versions(cls, key):
        return cls.objects.filter(key=key).delete()

    def __str__(self):
        return f"{self.key}={self.display_value!r} [v-{self.version}]"

    class Meta:
        permissions = (("edit_setting", "Can edit setting"),)
        unique_together = ("key", "version")
