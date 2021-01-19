FROM localhost/galaxy_ng/galaxy_ng:base

COPY requirements/requirements.standalone.in /tmp/requirements.standalone.txt
COPY requirements/constraints.standalone.txt /tmp/constraints.standalone.txt

RUN set -ex; \
    pip install --no-cache-dir --requirement /tmp/requirements.standalone.txt --constraint /tmp/constraints.standalone.txt
