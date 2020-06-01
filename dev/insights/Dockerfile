FROM localhost/galaxy_ng/galaxy_ng:base

COPY requirements/requirements.insights.txt /tmp/requirements.insights.txt
RUN set -ex; \
    pip install --no-cache-dir --requirement /tmp/requirements.insights.txt
