#!/venv/bin/python3
# -*- coding: utf-8 -*-

import atexit
import os
import re
import socket
import sys
import coverage

from pulpcore.tasking.entrypoint import worker

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])

    pid = os.getpid()
    hostname = socket.gethostname()
    data_file = f'/src/galaxy_ng/dev/standalone/.coverage.{hostname}.{pid}'

    cov = coverage.coverage(data_file=data_file)
    cov.start()

    def save_coverage():
        print('saving coverage!')
        cov.stop()
        cov.save()

    atexit.register(save_coverage)

    sys.exit(worker())
