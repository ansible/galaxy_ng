# Stage: Pulp bindings
# ---------------------------------------------------------
FROM openapitools/openapi-generator-cli AS bindings

COPY bindings/openapi.yaml /local/openapi.yaml
RUN docker-entrypoint.sh generate \
    -i /local/openapi.yaml \
    -g python \
    -o /local/galaxy-pulp \
    --skip-validate-spec \
    --additional-properties=packageName=galaxy_pulp,projectName=galaxy-pulp

# Stage: Base image
# ---------------------------------------------------------
FROM centos:8 AS base

# # Install missing en_US.UTF-8 locale
RUN dnf install -y \
        glibc-langpack-en \
        python3 \
    && dnf -y clean all
ENV LANG=en_US.UTF-8

# Stage: galaxy_api image
# ---------------------------------------------------------
FROM base

ENV PYTHONUNBUFFERED=1 \
    PULP_SETTINGS=/etc/pulp/settings.py \
    DJANGO_SETTINGS_MODULE=pulpcore.app.settings

# Install dependencies
RUN dnf -y install \
        gcc \
        python3-devel \
        libpq \
        libpq-devel \
    && dnf -y clean all

COPY . /app
COPY --from=bindings /local/galaxy-pulp /tmp/galaxy-pulp

RUN mkdir -p /var/run/pulp \
             /var/lib/pulp/tmp \
    && python3 -m venv /venv \
    && source /venv/bin/activate \
    && pip install --no-cache --upgrade pip \
    && pip install --no-cache /tmp/galaxy-pulp \
    && pip install --no-cache --editable /app \
    && PULP_CONTENT_ORIGIN=x django-admin collectstatic \
    && rm -rf /tmp/galaxy-pulp \
    && chmod 0755 /app/docker/entrypoint.sh \
                  /app/docker/scripts/*.sh \
    && mv /app/docker/entrypoint.sh /entrypoint.sh \
    && mv /app/docker/scripts/*.sh /usr/local/bin

ENV PATH="/venv/bin:${PATH}"

VOLUME [ "/var/lib/pulp/artifact", "/var/lib/pulp/tmp" ]

ENTRYPOINT [ "/entrypoint.sh" ]
