FROM registry.access.redhat.com/ubi8

ARG GIT_COMMIT
ARG USER_ID=1000

ENV LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PULP_SETTINGS=/etc/pulp/settings.py \
    DJANGO_SETTINGS_MODULE=pulpcore.app.settings \
    PATH="/venv/bin:${PATH}" \
    GIT_COMMIT=${GIT_COMMIT:-} \
    VIRTUAL_ENV="/venv"

RUN adduser --uid "${USER_ID}" -G 0 --home-dir /app --no-create-home galaxy

# https://access.redhat.com/security/cve/CVE-2021-3872
RUN rpm -qa | egrep ^vim | xargs rpm -e --nodeps

COPY requirements/requirements.insights.txt /tmp/requirements.txt

# Installing dependencies
# NOTE: en_US.UTF-8 locale is provided by glibc-langpack-en
RUN set -ex; \
    DNF="dnf -y --disableplugin=subscription-manager" && \
    INSTALL_PKGS="glibc-langpack-en git-core libpq python3.11 python3.11-pip gettext skopeo" && \
    INSTALL_PKGS_BUILD="gcc libpq-devel python3.11-devel openldap-devel" && \
    LANG=C ${DNF} install ${INSTALL_PKGS} ${INSTALL_PKGS_BUILD} && \
    python3.11 -m venv "${VIRTUAL_ENV}" && \
    PYTHON="${VIRTUAL_ENV}/bin/python3" && \
    ${PYTHON} -m pip install -U pip wheel && \
    ${PYTHON} -m pip install -r /tmp/requirements.txt && \
    ${DNF} autoremove ${INSTALL_PKGS_BUILD} && \
    ${DNF} clean all --enablerepo='*'

COPY . /app

# We need to force a consistent homedir for openshift, or it will
# default to the unwritable root directory.
ENV HOME="/app"

# https://developers.redhat.com/blog/2020/10/26/adapting-docker-and-kubernetes-containers-to-run-on-red-hat-openshift-container-platform#group_ownership_and_file_permission
# We have to make /app group writable because openshift always runs with an random UUID
RUN chgrp -R 0 $HOME && \
    chmod -R g=u $HOME

RUN set -ex; \
    install -dm 0775 -o galaxy \
                               /var/lib/pulp/{artifact,assets,media,scripts,tmp} \
                               /etc/pulp/{certs,keys} \
                               /tmp/ansible && \
    install -dm 0700 -o galaxy /etc/pulp/gnupg && \
    pip3.11 install --config-settings editable_mode=compat --no-deps --editable /app && \
    chown -R galaxy ${VIRTUAL_ENV} && \
    PULP_CONTENT_ORIGIN=x django-admin collectstatic && \
    install -Dm 0644 -o galaxy /app/ansible.cfg /etc/ansible/ansible.cfg && \
    install -Dm 0644 -o galaxy /app/docker/etc/settings.py /etc/pulp/settings.py && \
    install -Dm 0755 -o galaxy /app/docker/entrypoint.sh /entrypoint.sh && \
    install -Dm 0755 -o galaxy /app/docker/bin/* /usr/local/bin/ && \
    install -Dm 0775 -o galaxy /app/galaxy-operator/bin/* /usr/bin/

USER galaxy
WORKDIR /app
VOLUME [ "/var/lib/pulp", \
         "/etc/pulp", \
         "/tmp/ansible" ]
ENTRYPOINT [ "/entrypoint.sh" ]
