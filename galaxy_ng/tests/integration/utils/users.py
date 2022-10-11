import random
import string

from .client_ui import UIClient

def create_user(username, password, api_client=None):
    assert api_client is not None, "api_client is a required param"

    if password is None:
        password = ''.join([random.choice(string.printable) for x in range(0, 12)])

    payload = {
        "username": username,
        "first_name": "",
        "last_name": "",
        "email": "",
        "group": "",
        "password": password,
        "description": "",
    }

    if isinstance(api_client, UIClient):
        rr = api_client.post(f'_ui/v1/users/', payload=payload)
        assert rr.status_code == 201, rr.text
        return rr.json()

    api_prefix = api_client.config.get("api_prefix").rstrip("/")
    return api_client(f'{api_prefix}/_ui/v1/users/', args=payload, method='POST')


def delete_user(username, api_client=None):
    assert api_client is not None, "api_client is a required param"
    api_prefix = api_client.config.get("api_prefix").rstrip("/")

    # DELETE https://galaxy-ng-beta.tannerjc.net/api/_ui/v1/users/46/

    # Find the user first
    if isinstance(api_client, UIClient):
        rr = api_client.get(f'_ui/v1/users/?username={username}')
        resp = rr.json()
    else:
        resp = api_client(api_prefix + f'/_ui/v1/users/?username={username}')

    if resp['meta']['count'] == 0:
        return

    uinfo = resp['data'][0]
    uid = uinfo['id']

    if isinstance(api_client, UIClient):
        rr = api_client.delete(f'_ui/v1/users/{uid}')
        assert rr.status_code == 204
        return
    else:
        try:
            resp = api_client(api_prefix + f'/_ui/v1/users/{uid}/', method='DELETE')
        except Exception as e:
            error = str(e)
            assert 'as JSON' in error, e
