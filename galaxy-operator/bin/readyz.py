#!/usr/bin/env python3

import os
import sys
import requests

from requests.packages.urllib3.util.connection import HAS_IPV6
from django.conf import settings


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


if sys.argv[1] == settings.CONTENT_PATH_PREFIX:
    is_content_healthy(sys.argv[1])
else:
    is_api_healthy(sys.argv[1])
