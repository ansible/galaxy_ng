# NOTE: This Dockerfile is currently used to build release images. So it is leaved as is.
# It should be removed once migration to standalone Dockerfile for release images
# is complete.
FROM docker.io/centos:8

ARG USER_ID=1000
ARG USER_NAME=galaxy
ARG USER_GROUP=galaxy

ENV LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PULP_SETTINGS=/etc/pulp/settings.py \
    DJANGO_SETTINGS_MODULE=pulpcore.app.settings

RUN set -ex; \
    id --group "${USER_GROUP}" &>/dev/null \
    || groupadd --gid "${USER_ID}" "${USER_GROUP}"; \
    \
    useradd --uid ${USER_ID} --gid "${USER_GROUP}" "${USER_NAME}"

# Install dependencies:
#   * glibc-langpack-en: install missing en_US.UTF-8 locale
# NOTE(cutwater): This is a workaround for https://bugs.centos.org/view.php?id=16934
#   See also: https://bugzilla.redhat.com/show_bug.cgi?id=1680124#c6
RUN set -ex; \
    touch /var/lib/rpm/* \
    && dnf -y install \
        gcc \
        glibc-langpack-en \
        python3-devel \
        libpq \
        libpq-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf/ \
    && rm -f /var/lib/rpm/__db.* \
    \
    && python3 -m venv /venv

ENV PATH="/venv/bin:${PATH}" \
    VIRTUAL_ENV="/venv"

# Install python requirements
COPY ./requirements/requirements.insights.txt /tmp/requirements.txt

RUN set -ex; \
    pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --requirement /tmp/requirements.txt

# Install application
COPY . /app

RUN set -ex; \
    pip install --no-cache-dir --editable /app \
    && PULP_CONTENT_ORIGIN=x django-admin collectstatic

# Finalize installation
RUN set -ex; \
    mkdir -p /var/lib/pulp/artifact \
             /var/lib/pulp/tmp \
             /tmp/ansible \
             /etc/ansible \
             /entrypoints.d \
    && chown -R ${USER_NAME}:${USER_GROUP} \
        /app \
        /venv \
        /var/lib/pulp \
        /tmp/ansible \
        /etc/ansible \
    && chmod -R 0775 /var/lib/pulp \
                     /app/docker/entrypoint.sh \
                     /app/docker/bin/* \
                     /tmp/ansible \
    && mv /app/docker/entrypoint.sh /entrypoint.sh \
    && mv /app/ansible.cfg /etc/ansible/ansible.cfg \
    && mv /app/docker/bin/* /usr/local/bin

USER "${USER_NAME}"
VOLUME [ "/var/lib/pulp", "/tmp/ansible" ]
ENTRYPOINT [ "/entrypoint.sh" ]
