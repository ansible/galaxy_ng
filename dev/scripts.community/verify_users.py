#!/usr/bin/env python

import os
import json

from django.contrib.auth import get_user_model


User = get_user_model()



with open('verified_users.json', 'r') as f:
    umap = json.loads(f.read())

for user in User.objects.all():
    print(f'{user} {user.email}')
    if not user.email:
        continue

    if user.username not in umap:
        continue

    email = user.email
    if not email.endswith('@GALAXY.GITHUB.UNVERIFIED.COM'):
        continue

    expected_github_id = email.replace('@GALAXY.GITHUB.UNVERIFIED.COM', '')
    if expected_github_id == 'None':
        continue

    expected_github_id = int(expected_github_id)

    actual_github_id = umap.get(user.username)
    if umap.get(user.username) != expected_github_id:
        continue

    print(f'\tVERIFIED: {user.username} {expected_github_id} == {actual_github_id}')
    user.email = ''
    user.save()
    #import epdb; epdb.st()

