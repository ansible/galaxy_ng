#!/usr/bin/env python3

import os
import sys
import requests

from requests.packages.urllib3.util.connection import HAS_IPV6


def is_api_healthy(path):
    """
    Checks if API is healthy
    """
    address = "[::1]" if HAS_IPV6 else "127.0.0.1"
    url = f"http://{address}:8000{path}"
    print(f"Readiness probe: checking {url}")
    response = requests.get(url, allow_redirects=True)
    data = response.json()

    if not data["database_connection"]["connected"]:
        print("Readiness probe: database issue")
        sys.exit(3)

    if os.getenv("REDIS_SERVICE_HOST") and not data["redis_connection"]["connected"]:
        print("Readiness probe: cache issue")
        sys.exit(4)

    print("Readiness probe: ready!")
    sys.exit(0)


def is_content_healthy(path):
    """
    Checks if Content is healthy
    """
    address = "[::1]" if HAS_IPV6 else "127.0.0.1"
    url = f"http://{address}:24816{path}"
    print(f"Readiness probe checking {url}")
    response = requests.head(url)
    response.raise_for_status()

    print("Readiness probe: ready!")
    sys.exit(0)


"""
PID 1 value (/proc/1/cmdline) may vary based on the gunicorn install method (RPM vs pip)
The cmdline value for this PID looks like:
```
# pip installation
gunicorn: master [pulp-{content,api}]
```
OR
```
# RPM installation
/usr/bin/python3.9/usr/bin/gunicorn--bind[::]:2481{6,7}pulpcore.app.wsgi:application--namepulp-{api,content}--timeout90--workers2
```
"""
with open("/proc/1/cmdline") as f:
    cmdline = f.readline()

if "start-api" in cmdline:
    is_api_healthy(sys.argv[1])

elif "start-content-app" in cmdline:
    is_content_healthy(sys.argv[1])
