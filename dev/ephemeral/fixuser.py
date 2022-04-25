from galaxy_ng.app.models.auth import User

user, _ = User.objects.get_or_create(
    username='jdoe',
    defaults=dict(
        username='jdoe',
        password='bar'
    )
)
user.is_superuser = True
user.is_staff = True
user.save()
