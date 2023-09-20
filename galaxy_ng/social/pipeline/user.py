#!/usr/bin/env python3


from galaxy_ng.app.models.auth import User
from galaxy_ng.app.utils.galaxy import generate_unverified_email


USER_FIELDS = ['username', 'email']


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    return {'username': details['username']}


def create_user(strategy, details, backend, user=None, *args, **kwargs):

    if user:
        if user.username != details.get('username'):
            user.username = details.get('username')
            user.save()
        return {'is_new': False}

    fields = dict(
        (name, kwargs.get(name, details.get(name)))
        for name in backend.setting('USER_FIELDS', USER_FIELDS)
    )

    if not fields:
        return

    # bypass the strange logic that can't find the user ... ?
    username = details.get('username')
    email = details.get('email')
    github_id = details.get('id')
    if not github_id:
        github_id = kwargs['response']['id']

    # check for all possible emails ...
    possible_emails = [generate_unverified_email(github_id), email]
    for possible_email in possible_emails:
        found_email = User.objects.filter(email=possible_email).first()
        if found_email is not None:
            break

    if found_email is not None:

        # fix the username if they've changed their login since last time
        if found_email.username != username:
            found_email.username = username
            found_email.save()

        if found_email.email != email:
            found_email.email = email
            found_email.save()

        return {
            'is_new': False,
            'user': found_email
        }

    found_username = User.objects.filter(username=username).first()
    if found_username is not None and found_username.email:
        # we have an old user who's got the username but it's not the same person logging in ...
        # so change that username? The email should be unique right?
        found_username.username = found_username.email
        found_username.save()

    found_username = User.objects.filter(username=username).first()
    if found_username is not None:
        return {
            'is_new': False,
            'user': found_username
        }

    new_user = strategy.create_user(**fields)
    return {
        'is_new': True,
        'user': new_user
    }


def user_details(strategy, details, backend, user=None, *args, **kwargs):
    """Update user details using data from provider."""

    if not user:
        return

    changed = False  # flag to track changes

    # Default protected user fields (username, id, pk and email) can be ignored
    # by setting the SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS to True
    if strategy.setting("NO_DEFAULT_PROTECTED_USER_FIELDS") is True:
        protected = ()
    else:
        protected = (
            "username",
            "id",
            "pk",
            "email",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
        )

    protected = protected + tuple(strategy.setting("PROTECTED_USER_FIELDS", []))

    # Update user model attributes with the new data sent by the current
    # provider. Update on some attributes is disabled by default, for
    # example username and id fields. It's also possible to disable update
    # on fields defined in SOCIAL_AUTH_PROTECTED_USER_FIELDS.
    field_mapping = strategy.setting("USER_FIELD_MAPPING", {}, backend)
    for name, value in details.items():
        # Convert to existing user field if mapping exists
        name = field_mapping.get(name, name)
        if value is None or not hasattr(user, name) or name in protected:
            continue

        current_value = getattr(user, name, None)
        if current_value == value:
            continue

        immutable_fields = tuple(strategy.setting("IMMUTABLE_USER_FIELDS", []))
        if name in immutable_fields and current_value:
            continue

        changed = True
        setattr(user, name, value)

    if changed:
        strategy.storage.user.changed(user)
