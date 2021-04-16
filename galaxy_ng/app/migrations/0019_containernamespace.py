from django.db import migrations
import django_lifecycle.mixins
import galaxy_ng.app.access_control.mixins

class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0018_set_rate_limit_default'),
        ('container', '0018_containerdistribution_description')
    ]

    operations = [
        migrations.CreateModel(
            name='ContainerNamespace',
            fields=[
            ],
            options={
                'proxy': True,
                'default_related_name': '%(app_label)s_%(model_name)s',
                'indexes': [],
                'constraints': [],
            },
            bases=('container.containernamespace', django_lifecycle.mixins.LifecycleModelMixin, galaxy_ng.app.access_control.mixins.GroupModelPermissionsMixin),
        ),
    ]
