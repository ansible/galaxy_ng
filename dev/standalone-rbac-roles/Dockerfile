ARG DEV_IMAGE_SUFFIX

FROM localhost/galaxy_ng/galaxy_ng:base${DEV_IMAGE_SUFFIX:-}

COPY requirements/requirements.standalone.txt /tmp/requirements.standalone.txt

RUN set -ex; \
    if [[ "${LOCK_REQUIREMENTS}" -eq "1" ]]; then \
    pip install --no-cache-dir --requirement /tmp/requirements.standalone.txt; \
    fi

USER root

RUN dnf install -y gettext;

USER galaxy
