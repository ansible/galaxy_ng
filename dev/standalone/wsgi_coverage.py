"""
WSGI config for pulp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import atexit
import os
import socket
import sys
import coverage

from django.core.wsgi import get_wsgi_application  # noqa

pid = os.getpid()
hostname = socket.gethostname()
data_file = f'/src/galaxy_ng/dev/standalone/.coverage.{hostname}.{pid}'

cov = coverage.coverage(
    data_file=data_file,
    #concurrency='multiprocessing',
    #config_file=False
)
cov.start()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")

application = get_wsgi_application()

def save_coverage():
    print('saving coverage!')
    cov.stop()
    cov.save()

atexit.register(save_coverage)
