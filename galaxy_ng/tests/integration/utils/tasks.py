"""Utility functions for AH tests."""

import time

from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_POLLING
from .urls import url_safe_join
from .errors import (
    TaskWaitingTimeout
)


def wait_for_task(api_client, resp, timeout=300):
    ready = False
    url = url_safe_join(api_client.config["url"], resp["task"])
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        try:
            resp = api_client(url)
        except GalaxyError as e:
            if "500" not in str(e):
                raise
        else:
            ready = resp["state"] not in ("running", "waiting")
        time.sleep(SLEEP_SECONDS_POLLING)
    return resp


def wait_for_task_ui_client(uclient, task):
    counter = 0
    state = None
    while state in [None, 'waiting', 'running']:
        counter += 1
        if counter >= 60:
            raise Exception('Task is taking too long')
        resp = uclient.get(absolute_url=task['task'])
        assert resp.status_code == 200
        ds = resp.json()
        state = ds['state']
        if state == 'completed':
            break
        time.sleep(SLEEP_SECONDS_POLLING)
    assert state == 'completed'
