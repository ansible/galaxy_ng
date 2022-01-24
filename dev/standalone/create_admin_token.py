from galaxy_ng.app.models.auth import User
from rest_framework.authtoken.models import Token

print('find admin user ...')
admin = User.objects.filter(username="admin")[0]
print('delete existing tokens for admin ...')
Token.objects.filter(user=admin).delete()
print('create new token for admin ...')
Token.objects.create(user=admin, key="abcdefghijklmnopqrstuvwxyz1234567890")
