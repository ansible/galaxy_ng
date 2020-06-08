FROM localhost/galaxy_ng/galaxy_ng:base

COPY requirements/requirements.standalone.txt /tmp/requirements.standalone.txt

RUN set -ex; \
    pip install --no-cache-dir --requirement /tmp/requirements.standalone.txt
