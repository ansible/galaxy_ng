from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0050_organization_data"),
    ]

    operations = [
        migrations.RenameField(
            model_name="organization",
            old_name="created_on",
            new_name="created",
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="modified_on",
            new_name="modified",
        ),
        migrations.RenameField(
            model_name="team",
            old_name="created_on",
            new_name="created"
        ),
        migrations.RenameField(
            model_name="team",
            old_name="modified_on",
            new_name="modified",
        ),
        migrations.AlterField(
            model_name="organization",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, help_text="The date/time this resource was created"
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="modified",
            field=models.DateTimeField(
                auto_now=True, help_text="The date/time this resource was created"
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, help_text="The date/time this resource was created"
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="modified",
            field=models.DateTimeField(
                auto_now=True, help_text="The date/time this resource was created"
            ),
        ),
    ]
