from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Lower
from django_lifecycle import (
    LifecycleModelMixin,
    hook,
    AFTER_CREATE,
    AFTER_DELETE,
    BEFORE_CREATE,
)


__all__ = ['Setting']


class SettingsManager(models.Manager):
    def create(self, *args, **kwargs):
        """Increase version field on create."""
        # TODO: Acquire lock (use pulp task manager? or a transaction atomic?)
        existing = self.get_queryset().filter(key=kwargs['key'])
        if existing:
            kwargs['version'] = existing.latest('version').version + 1
        # TODO: Validate key value pair
        new =  super().create(*args, **kwargs)
        # TODO: Release lock
        # TODO: Keep only 10 latest versions
        return new

    def filter(self, *args, **kwargs):
        """case insensitive filter"""
        if 'key' in kwargs:
            kwargs['key__iexact'] = kwargs.pop('key')
        return super().filter(*args, **kwargs)


class Setting(LifecycleModelMixin, models.Model):
    objects = SettingsManager()

    key = models.CharField(max_length=255, null=False)
    value = models.TextField(blank=False, null=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        editable=False,
        default=None,
        related_name='settings'
    )
    version = models.IntegerField(default=1, null=False)
    is_secret = models.BooleanField(default=False, null=False)

    @hook(AFTER_CREATE, on_commit=True)
    def _hook_update_create(self):
        print("update_cache via Cache client", self.key, self.value, self.version)

    @hook(AFTER_DELETE, on_commit=True)
    def _hook_delete_cache(self):
        # TODO: one method to delete only latest version
        # TODO: one method to delete all versions
        print("delete_cache via Cache client")

    @hook(BEFORE_CREATE)
    def _hook_validate(self):
        print(settings.get("SETTINGS_ALLOWED_KEYS", []))
        print("validate via settings validators")

    @property
    def display_value(self):
        return f"{self.value[:3]}***" if self.is_secret else self.value

    @classmethod
    def get_value_from_db(cls, key):
        return cls.get_setting_from_db(key).value

    @classmethod
    def get_setting_from_db(cls, key):
        return cls.objects.filter(key=key).latest('version')

    @classmethod
    def get_all(cls):
        return (
            cls.objects
            .annotate(key_lower=Lower('key'))
            .order_by('key_lower', '-version')
            .distinct('key_lower')
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
        return cls.objects.filter(key=key).latest('version').delete()

    @classmethod
    @transaction.atomic
    def delete_all_versions(cls, key):
        return cls.objects.filter(key=key).delete()

    def __str__(self):
        return f"{self.key}={self.display_value!r} [v-{self.version}]"

    class Meta:
        permissions = (
            ('edit_setting', 'Can edit setting'),
        )
        unique_together = ('key', 'version')
