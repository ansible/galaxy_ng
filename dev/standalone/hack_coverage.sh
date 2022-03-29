#!/bin/bash

echo "HACKING COVERAGE!!!"

# /venv/bin/python -c 'from pulpcore.app import wsgi; print(wsgi.__file__)'
#   /venv/lib64/python3.8/site-packages/pulpcore/app/wsgi.py
WSGI_FILE=/venv/lib64/python3.8/site-packages/pulpcore/app/wsgi.py
rm -f ${WSGI_FILE}
cp /src/galaxy_ng/dev/standalone/wsgi_coverage.py ${WSGI_FILE}

# /usr/local/bin/start-worker
#   exec pulpcore-worker
#       /venv/bin/pulpcore-worker
WORKER_SCRIPT=/venv/bin/pulpcore-worker
rm -f ${WORKER_SCRIPT}
cp /src/galaxy_ng/dev/standalone/worker_coverage.py ${WORKER_SCRIPT}
chmod +x ${WORKER_SCRIPT}

/venv/bin/pip install --upgrade coverage
