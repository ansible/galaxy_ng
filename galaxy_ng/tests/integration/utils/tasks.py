"""Utility functions for AH tests."""
import logging
import time

from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_POLLING
from .urls import url_safe_join
from .errors import (
    TaskWaitingTimeout
)

logger = logging.getLogger(__name__)


def wait_for_all_tasks(client, timeout=300):
    ready = False
    wait_until = time.time() + timeout

    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = client(
            "pulp/api/v3/tasks/?state=running",
        )["count"]

        waiting_count = client(
            "pulp/api/v3/tasks/?state=waiting",
        )["count"]

        ready = running_count == 0 and waiting_count == 0

        time.sleep(SLEEP_SECONDS_POLLING)


def wait_for_all_tasks_gk(gc, timeout=300):
    ready = False
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = gc.get("pulp/api/v3/tasks/?state=running")["count"]
        waiting_count = gc.get("pulp/api/v3/tasks/?state=waiting")["count"]
        ready = running_count == 0 and waiting_count == 0
        time.sleep(SLEEP_SECONDS_POLLING)


def wait_for_task(api_client, resp, task_id=None, timeout=6000, raise_on_error=False):
    if task_id:
        url = f"v3/tasks/{task_id}/"
    else:
        url = url_safe_join(api_client.config["url"], resp["task"])

    ready = False
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        try:
            resp = api_client(url)
            if resp["state"] == "failed":
                logger.error(resp["error"])
                if raise_on_error:
                    raise TaskFailed(resp["error"])
        except GalaxyError as e:
            raise e
            # if "500" not in str(e):
            #    raise
        else:
            ready = resp["state"] not in ("running", "waiting")
        time.sleep(SLEEP_SECONDS_POLLING)
    return resp


def wait_for_task_ui_client(gc, task):
    counter = 0
    state = None
    task_id = task["task"].split("v3/tasks/")[1][:-1]
    while state in [None, 'waiting', 'running']:
        counter += 1
        if counter >= 60:
            raise Exception('Task is taking too long')
        ds = gc.get(f"pulp/api/v3/tasks/{task_id}/")
        try:
            state = ds.json()['state']
        except AttributeError:
            state = ds['state']
        if state == 'completed':
            break
        time.sleep(SLEEP_SECONDS_POLLING)
    assert state == 'completed', ds


def wait_for_namespace_tasks_gk(gc, timeout=300):
    ready = False
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        running_count = gc.get("pulp/api/v3/tasks/?state=running&name__contains=namespace")["count"]
        waiting_count = gc.get("pulp/api/v3/tasks/?state=waiting&name__contains=namespace")["count"]
        ready = running_count == 0 and waiting_count == 0
        time.sleep(SLEEP_SECONDS_POLLING)


class TaskFailed(Exception):
    def __init__(self, message):
        self.message = message
