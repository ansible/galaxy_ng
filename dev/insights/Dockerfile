ARG DEV_IMAGE_SUFFIX

FROM localhost/galaxy_ng/galaxy_ng:base${DEV_IMAGE_SUFFIX:-}

COPY requirements/requirements.insights.txt /tmp/requirements.insights.txt
RUN set -ex; \
    pip install --no-cache-dir --requirement /tmp/requirements.insights.txt
