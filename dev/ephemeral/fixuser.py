from galaxy_ng.app.models.auth import Group, User

pe_group = Group.objects.get(name="system:partner-engineers")

user = User.objects.create_user('jdoe', password='bar')
# user.is_superuser = True
# user.is_staff = True
user.groups.add(pe_group)
user.save()
