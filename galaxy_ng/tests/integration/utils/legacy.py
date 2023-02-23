import time

from .client_ansible_lib import get_client
from .namespaces import cleanup_namespace
from .users import (
    delete_group,
    delete_user,
)


def wait_for_v1_task(task_id=None, resp=None, api_client=None):

    if task_id is None:
        task_id = resp['task']

    # poll till done or timeout
    poll_url = f'/api/v1/tasks/{task_id}/'

    state = None
    counter = 0
    while state is None or state == 'RUNNING' and counter <= 500:
        counter += 1
        task_resp = api_client(poll_url, method='GET')
        state = task_resp['results'][0]['state']
        if state != 'RUNNING':
            break
        time.sleep(.5)

    assert state == 'SUCCESS'


def clean_all_roles(ansible_config):

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    pre_existing = []
    next_url = '/api/v1/roles/'
    while next_url:
        resp = admin_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']

    usernames = [x['username'] for x in pre_existing]
    usernames = sorted(set(usernames))
    for username in usernames:
        cleanup_social_user(username, ansible_config)


def cleanup_social_user(username, ansible_config):
    """ Should delete everything related to a social auth'ed user. """

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # delete any pre-existing roles from the user
    pre_existing = []
    next_url = f'/api/v1/roles/?owner__username={username}'
    while next_url:
        resp = admin_client(next_url)
        pre_existing.extend(resp['results'])
        if resp['next'] is None:
            break
        next_url = resp['next']
    if pre_existing:
        for pe in pre_existing:
            role_id = pe['id']
            role_url = f'/api/v1/roles/{role_id}/'
            try:
                resp = admin_client(role_url, method='DELETE')
            except Exception:
                pass

    # cleanup the v1 namespace
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    if resp['count'] > 0:
        for result in resp['results']:
            ns_url = f"/api/v1/namespaces/{result['id']}/"
            try:
                admin_client(ns_url, method='DELETE')
            except Exception:
                pass
    resp = admin_client(f'/api/v1/namespaces/?name={username}', method='GET')
    assert resp['count'] == 0

    namespace_name = username.replace('-', '_').lower()

    # cleanup the v3 namespace
    cleanup_namespace(namespace_name, api_client=get_client(config=ansible_config("admin")))

    # cleanup the group
    delete_group(username, api_client=get_client(config=ansible_config("admin")))
    delete_group(
        'namespace:' + namespace_name,
        api_client=get_client(config=ansible_config("admin"))
    )

    # cleanup the user
    delete_user(username, api_client=get_client(config=ansible_config("admin")))
