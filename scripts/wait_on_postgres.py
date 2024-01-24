#!/usr/bin/env python3

import sys
import time
from django.db import connection, utils

if __name__ == "__main__":

    print("Waiting on postgresql to start...")
    for dummy in range(100):
        try:
            connection.ensure_connection()
            break
        except utils.OperationalError:
            time.sleep(3)

    else:
        print("Unable to reach postgres.")
        sys.exit(1)

    print("Postgres started.")
    sys.exit(0)
