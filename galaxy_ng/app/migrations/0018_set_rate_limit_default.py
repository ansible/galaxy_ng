from django.db import migrations

def set_rate_limit_default(apps, schema_editor):
    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')

    # By default pulp core sets the new rate_limit field to null, which remotes the
    # rate limit. This breaks cloud.redhat.com during collection syncs. This sets the
    # default to 8, which should be low enough to not break all of our customer's
    # collection syncs.
    CollectionRemote.objects.all().update(rate_limit=8)


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0017_populate_repos_and_remotes'),
    ]

    operations = [
        migrations.RunPython(
            code=set_rate_limit_default,
            reverse_code=migrations.RunPython.noop
        )
    ]
