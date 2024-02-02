FROM registry.access.redhat.com/ubi8

ARG GIT_COMMIT

ENV LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PULP_SETTINGS=/etc/pulp/settings.py \
    DJANGO_SETTINGS_MODULE=pulpcore.app.settings \
    PATH="/venv/bin:${PATH}" \
    GIT_COMMIT=${GIT_COMMIT:-} \
    VIRTUAL_ENV="/venv"

RUN adduser --uid 1000 --gid 0 --home-dir /app --no-create-home galaxy

# https://access.redhat.com/security/cve/CVE-2021-3872
RUN rpm -qa | egrep ^vim | xargs rpm -e --nodeps

COPY requirements/requirements.insights.txt /tmp/requirements.txt

# Installing dependencies
# NOTE: en_US.UTF-8 locale is provided by glibc-langpack-en
RUN set -ex; \
    DNF="dnf -y --disableplugin=subscription-manager" && \
    INSTALL_PKGS="glibc-langpack-en git-core libpq python3.11 python3.11-pip skopeo" && \
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
                               /var/lib/pulp/{artifact,media,scripts,tmp} \
                               /etc/pulp/{certs,keys} \
                               /tmp/ansible && \
    pip3.11 install --no-deps --editable /app && \
    PULP_CONTENT_ORIGIN=x django-admin collectstatic && \
    install -Dm 0644 /app/ansible.cfg /etc/ansible/ansible.cfg && \
    install -Dm 0644 /app/docker/etc/settings.py /etc/pulp/settings.py && \
    install -Dm 0755 /app/docker/entrypoint.sh /entrypoint.sh && \
    install -Dm 0755 /app/docker/bin/* /usr/local/bin/

# DEV (start)
# Adding operator support
#
# Install python nginx package
RUN pip3 install python-nginx

COPY scripts/* /usr/bin/

# Pre-create things we need to access
RUN for file in \
      /usr/bin/route_paths.py \
      /usr/bin/wait_on_postgres.py \
      /usr/bin/readyz.py ; \
    do touch $file ; chmod g+rw+x $file ; chgrp root $file ; done

# DEV (end)

USER galaxy
WORKDIR /app
VOLUME [ "/var/lib/pulp", \     
         "/tmp/ansible" ]
ENTRYPOINT [ "/entrypoint.sh" ]