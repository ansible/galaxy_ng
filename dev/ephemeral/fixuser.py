from galaxy_ng.app.models.auth import User

user = User.objects.filter(username='jdoe').first()
if user is None:
    user = User.objects.create_user('jdoe', password='bar')

user.is_superuser = True
user.is_staff = True
user.save()
