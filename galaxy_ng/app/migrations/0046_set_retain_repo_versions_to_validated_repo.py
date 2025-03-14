from django.db import migrations


def set_retain_repo_versions_to_validated_repo(apps, schema_editor):
    AnsibleRepository = apps.get_model('ansible', 'AnsibleRepository')

    db_alias = schema_editor.connection.alias

    validated_repo = AnsibleRepository.objects.using(db_alias).filter(name="validated").first()
    if validated_repo and validated_repo.retain_repo_versions is None:
        validated_repo.retain_repo_versions = 1
        validated_repo.save()


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0045_setting"),
    ]

    operations = [
        migrations.RunPython(
            code=set_retain_repo_versions_to_validated_repo,
            reverse_code=migrations.RunPython.noop
        ),
    ]