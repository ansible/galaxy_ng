from galaxy_ng.app.models.auth import User
from rest_framework.authtoken.models import Token

print('find jdoe user ...')
jdoe = User.objects.filter(username="jdoe")[0]

print('delete existing tokens for jdoe ...')
Token.objects.filter(user=jdoe).delete()

print('create new token for jdoe ...')
Token.objects.create(user=jdoe, key="abcdefghijklmnopqrstuvwxyz1234567890")
