#!/usr/bin/env python3

import logging


logger = logging.getLogger(__name__)


USER_FIELDS = ['username', 'email']


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    return {'username': details['username']}


def create_user(strategy, details, backend, user=None, *args, **kwargs):

    if user:
        logger.info(f'create_user(1): user-kwarg:{user}:{user.id}')
    else:
        logger.info(f'create_user(1): user-kwarg:{user}')
    logger.info(f'create_user(2): details:{details}')

    if user:
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

    # bypass the strange logic that can't find the user ... ?
    username = details.get('username')
    email = details.get('email')
    github_id = details.get('id')
    if not github_id:
        github_id = kwargs['response']['id']
    logger.info(
        f'create_user(4): enumerate username:{username} email:{email} github_id:{github_id}'
    )

    new_user = strategy.create_user(**fields)
    logger.info(f'create_user(13): {new_user}')
    return {
        'is_new': True,
        'user': new_user
    }
