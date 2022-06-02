from galaxy_ng.app.models.auth import User
from rest_framework.authtoken.models import Token

# Get or create test users to match keycloak passwords
basic_user, _ = User.objects.get_or_create(username="iqe_normal_user")
basic_user.set_password("redhat")

partner_engineer, _ = User.objects.get_or_create(username="jdoe")
partner_engineer.set_password("redhat")

org_admin, _ = User.objects.get_or_create(username="org-admin")
org_admin.set_password("redhat")

admin, _ = User.objects.get_or_create(username="notifications_admin")
admin.set_password("redhat")
admin.is_superuser = True
admin.is_staff = True
admin.save()


# Get or create tokens for test users
Token.objects.get_or_create(user=basic_user, key="abcdefghijklmnopqrstuvwxyz1234567891")
Token.objects.get_or_create(user=partner_engineer, key="abcdefghijklmnopqrstuvwxyz1234567892")
Token.objects.get_or_create(user=org_admin, key="abcdefghijklmnopqrstuvwxyz1234567893")
Token.objects.get_or_create(user=admin, key="abcdefghijklmnopqrstuvwxyz1234567894")
