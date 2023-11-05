# Generated by Django 4.2.6 on 2023-11-01 19:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0107_distribution_hidden"),
        ("galaxy", "0042_namespace_created_namespace_updated"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegacyRoleImport",
            fields=[
                (
                    "task",
                    models.OneToOneField(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="+",
                        serialize=False,
                        to="core.task",
                    ),
                ),
                ("messages", models.JSONField(default=list, editable=False)),
            ],
            options={
                "ordering": ["task__pulp_created"],
            },
        ),
    ]