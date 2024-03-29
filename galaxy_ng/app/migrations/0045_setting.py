# Generated by Django 4.2.3 on 2023-07-21 15:45

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0044_legacyroleimport"),
    ]

    operations = [
        migrations.CreateModel(
            name="Setting",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^(?!\\d)[a-zA-Z0-9_]+$",
                                "alphanumeric, no spaces, no hyphen, only underscore cant start with a number.",
                            )
                        ],
                    ),
                ),
                ("value", models.TextField()),
                ("version", models.IntegerField(default=1)),
                ("is_secret", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        default=None,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "permissions": (("edit_setting", "Can edit setting"),),
                "unique_together": {("key", "version")},
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
