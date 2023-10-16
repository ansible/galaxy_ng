#!/usr/bin/env python3

import logging

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.utils.galaxy import generate_unverified_email


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

    # check for all possible emails ...
    possible_emails = [generate_unverified_email(github_id)]
    if email:
        possible_emails.append(email)

    found_email = None
    for possible_email in possible_emails:

        # if the email is null maybe that causes the user hijacking?
        if not possible_email:
            continue

        found_email = User.objects.filter(email=possible_email).first()
        if found_email is not None:
            logger.info(
                f'create_user(5): found user {found_email}:{found_email.id}'
                + f' via email {possible_email}'
            )
            break

    if found_email is not None:

        # fix the username if they've changed their login since last time
        if found_email.username != username:
            logger.info(
                f'create_user(6): set found user {found_email}:{found_email.id}'
                + f' username to {username}'
            )
            found_email.username = username
            found_email.save()

        if found_email.email != email:
            logger.info(
                f'create_user(7): set found user {found_email}:{found_email.id}'
                + f' email to {email}'
            )
            found_email.email = email
            found_email.save()

        logger.info(
            f'create_user(8): returning found user {found_email}:{found_email.id}'
            + f' via email {possible_email}'
        )
        return {
            'is_new': False,
            'user': found_email
        }

    logger.info(f'create_user(9): did not find any users via matching emails {possible_emails}')

    found_username = User.objects.filter(username=username).first()
    if found_username:
        logger.info(
            f'create_user(10): found user:{found_username}:{found_username.id}:'
            + f'{found_username.email}'
            + f' by username:{username}'
        )

    if found_username is not None and found_username.email:
        # we have an old user who's got the username but it's not the same person logging in ...
        # so change that username? The email should be unique right?
        logger.info(
            f'create_user(11): set {found_username}:{found_username.id}:{found_username.email}'
            + f' username to {found_username.email}'
        )
        found_username.username = found_username.email
        found_username.save()

    found_username = User.objects.filter(username=username).first()
    if found_username is not None:
        logger.info(f'create_user(12): {found_username}')
        return {
            'is_new': False,
            'user': found_username
        }

    new_user = strategy.create_user(**fields)
    logger.info(f'create_user(13): {new_user}')
    return {
        'is_new': True,
        'user': new_user
    }
