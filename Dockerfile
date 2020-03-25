FROM centos:8

ENV LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PULP_SETTINGS=/etc/pulp/settings.py \
    DJANGO_SETTINGS_MODULE=pulpcore.app.settings

# Install dependencies
RUN dnf -y install \
        glibc-langpack-en \
        gcc \
        python3 \
        python3-devel \
        libpq \
        libpq-devel \
    && dnf -y clean all

COPY . /app

RUN mkdir -p /var/run/pulp \
             /var/lib/pulp/tmp \
    && python3 -m venv /venv \
    && source /venv/bin/activate \
    && pip install --no-cache --upgrade pip \
    && pip install --no-cache --editable /app \
    && PULP_CONTENT_ORIGIN=x django-admin collectstatic \
    && chmod 0755 /app/docker/entrypoint.sh \
                  /app/docker/scripts/*.sh \
    && mv /app/docker/entrypoint.sh /entrypoint.sh \
    && mv /app/docker/scripts/*.sh /usr/local/bin

ENV PATH="/venv/bin:${PATH}"

VOLUME [ "/var/lib/pulp/artifact", "/var/lib/pulp/tmp" ]

ENTRYPOINT [ "/entrypoint.sh" ]
