#!/usr/bin/env python3

import copy
import random

import pytest

from ..utils import UIClient


REGEX_403 = r"HTTP Code: 403"


@pytest.mark.deployment_standalone
@pytest.mark.api_ui
@pytest.mark.min_hub_version("4.9dev")
@pytest.mark.skip_in_gw
def test_api_ui_v1_namespace_owners_users_and_group_separation(ansible_config):

    # https://issues.redhat.com/browse/AAH-3121
    # Namespace owners should have a list of users that are directly added as owners.
    # That list of users should -not- include users of groups that have been
    # added as owners.
    # TODO: make this test compatible with GW

    cfg = ansible_config('partner_engineer')
    with UIClient(config=cfg) as uclient:

        suffix = random.choice(range(0, 1000))
        group_name = f'group{suffix}'
        user_name = f'user{suffix}'
        namespace_name = f'namespace{suffix}'

        # make the group
        group_resp = uclient.post('_ui/v1/groups/', payload={'name': group_name})
        assert group_resp.status_code == 201
        group_ds = group_resp.json()

        # make the user & add it to the group
        user_resp = uclient.post(
            '_ui/v1/users/',
            payload={
                'username': user_name,
                'first_name': 'foo',
                'last_name': 'bar',
                'email': 'foo@barz.com',
                'groups': [group_ds],
                'password': 'abcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()-+',
                'is_superuser': False
            }
        )
        assert user_resp.status_code == 201

        # make the second user & don't add it to the group
        user2_name = f'user{suffix}2'
        user2_resp = uclient.post(
            '_ui/v1/users/',
            payload={
                'username': user2_name,
                'first_name': 'foo2',
                'last_name': 'bar2',
                'email': 'foo2@barz.com',
                'groups': [],
                'password': 'abcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()-+',
                'is_superuser': False
            }
        )
        assert user2_resp.status_code == 201
        user2_ds = user2_resp.json()

        # Create the namespace ...
        namespace_resp = uclient.post(
            '_ui/v1/namespaces/',
            payload={
                'name': namespace_name,
            }
        )
        namespace_ds = namespace_resp.json()

        # Add the user and the group to the namespace
        user2_payload = copy.deepcopy(user2_ds)
        user2_payload['object_roles'] = ['galaxy.collection_namespace_owner']
        group_payload = copy.deepcopy(group_ds)
        group_payload['object_roles'] = ['galaxy.collection_namespace_owner']
        uclient.put(
            f'_ui/v1/namespaces/{namespace_name}/',
            payload={
                'name': namespace_name,
                'id': namespace_ds['id'],
                'pulp_href': namespace_ds['pulp_href'],
                'users': [user2_payload],
                'groups': [group_payload],
            }
        )

        # Make sure the user list is the group and user2, but not user1 ...
        new_namespace_resp = uclient.get(f'_ui/v1/namespaces/{namespace_name}/')
        new_namespace_ds = new_namespace_resp.json()
        assert len(new_namespace_ds['groups']) == 1, new_namespace_ds['groups']
        assert len(new_namespace_ds['users']) == 1, new_namespace_ds['users']
        assert [x['name'] for x in new_namespace_ds['groups']] == [group_name]
        assert [x['name'] for x in new_namespace_ds['users']] == [user2_name]
