#!/usr/bin/env python3


from galaxy_ng.app.models.auth import User


USER_FIELDS = ['username', 'email']


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    return {'username': details['username']}


def create_user(strategy, details, backend, user=None, *args, **kwargs):

    if user:
        return {'is_new': False}

    fields = dict(
        (name, kwargs.get(name, details.get(name)))
        for name in backend.setting('USER_FIELDS', USER_FIELDS)
    )

    if not fields:
        return

    # bypass the strange logic that can't find the user ... ?
    username = details.get('username')
    if username:
        found_user = User.objects.filter(username=username).first()
        if found_user is not None:
            return {
                'is_new': False,
                'user': found_user
            }

    new_user = strategy.create_user(**fields)
    return {
        'is_new': True,
        'user': new_user
    }
