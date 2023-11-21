#!/usr/bin/env python3

import logging


logger = logging.getLogger(__name__)


USER_FIELDS = ['username', 'email']


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    return {'username': details['username']}


def create_user(strategy, details, backend, user=None, *args, **kwargs):

    if user:
        # update username if changed ...
        if user.username != details.get('username'):
            user.username = details.get('username')
            user.save()
        logger.info(f'create_user(2): returning user-kwarg {user}:{user.id}')
        return {'is_new': False}

    fields = dict(
        (name, kwargs.get(name, details.get(name)))
        for name in backend.setting('USER_FIELDS', USER_FIELDS)
    )

    if not fields:
        logger.info(f'create_user(3): no fields for {user}:{user.id}')
        return

    return {
        'is_new': True,
        'user': strategy.create_user(**fields)
    }
