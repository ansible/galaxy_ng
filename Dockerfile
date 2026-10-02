# --- Builder: compile pysequoia (dralley fork) wheel with crypto-policy support ---
FROM registry.access.redhat.com/ubi9 AS pysequoia-builder

RUN dnf -y --disableplugin=subscription-manager install \
        clang gcc git-core python3.12 python3.12-pip python3.12-devel openssl-devel && \
    dnf -y --disableplugin=subscription-manager clean all

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN python3.12 -m pip wheel --no-cache-dir --wheel-dir /wheels \
    git+https://github.com/dralley/pysequoia.git@d6dce71daa90d11c0059ec086794b5a7927d599d

# --- Main image ---
FROM registry.access.redhat.com/ubi9

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
    INSTALL_PKGS="glibc-langpack-en git-core libpq python3.12 python3.12-pip gettext skopeo" && \
    INSTALL_PKGS_BUILD="gcc libpq-devel python3.12-devel openldap-devel" && \
    LANG=C ${DNF} install ${INSTALL_PKGS} ${INSTALL_PKGS_BUILD} && \
    python3.12 -m venv "${VIRTUAL_ENV}" && \
    PYTHON="${VIRTUAL_ENV}/bin/python3" && \
    ${PYTHON} -m pip install -U pip wheel && \
    ${PYTHON} -m pip install -r /tmp/requirements.txt && \
    ${DNF} autoremove ${INSTALL_PKGS_BUILD} && \
    ${DNF} clean all --enablerepo='*'

# Replace upstream pysequoia with the dralley fork (adds StandardPolicy +
# system crypto-policy support).  The wheel is bind-mounted from the builder
# stage so it leaves no trace in the final image layers.
RUN --mount=type=bind,from=pysequoia-builder,source=/wheels,target=/tmp/pysequoia-wheels \
    ${VIRTUAL_ENV}/bin/pip install --no-cache-dir --no-index \
        --force-reinstall /tmp/pysequoia-wheels/pysequoia*.whl

# Patch pulpcore to use system crypto-policy when verifying signatures.
# Without this, gpg_verify() uses the built-in default policy which rejects
# keys with SHA-1 self-signatures (e.g. the Ansible Automation Hub 1 key).
RUN UTIL_PY=$(find ${VIRTUAL_ENV} -path '*/pulpcore/app/util.py' -print -quit) && \
    sed -i \
        -e 's/from pysequoia import Cert, Sig, verify/from pysequoia import Cert, Sig, StandardPolicy, verify/' \
        -e 's/result = verify(file=detached_data, store=store, signature=sig)/result = verify(file=detached_data, store=store, signature=sig, policy=StandardPolicy.from_system_config())/' \
        -e 's/result = verify(bytes=sig_data, store=store)/result = verify(bytes=sig_data, store=store, policy=StandardPolicy.from_system_config())/' \
        "$UTIL_PY"

# Additive crypto-policy for sequoia: DEFAULT + SHA-1 allowed.
# Keys created with GnuPG v2.0.x used SHA-1 for self-signatures;
# without this config pysequoia rejects them.
COPY docker/etc/sequoia-sha1.config /etc/crypto-policies/back-ends/sequoia.config

COPY . /app

WORKDIR /app

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
    pip3.12 install --config-settings editable_mode=compat --no-deps --editable /app && \
    chown -R galaxy ${VIRTUAL_ENV} && \
    PULP_REDIRECT_TO_OBJECT_STORAGE=false PULP_CONTENT_ORIGIN=x django-admin collectstatic && \
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /tmp/database_fields.symmetric.key && \
    cd galaxy_ng && \
    PULP_DB_ENCRYPTION_KEY=/tmp/database_fields.symmetric.key PULP_SETTINGS=/etc/pulp/setings.py django-admin compilemessages && \
    rm -f /tmp/database_fields.symmetric.key && \
    install -Dm 0644 -o galaxy /app/ansible.cfg /etc/ansible/ansible.cfg && \
    install -Dm 0644 -o galaxy /app/docker/etc/settings.py /etc/pulp/settings.py && \
    install -Dm 0755 -o galaxy /app/docker/entrypoint.sh /entrypoint.sh && \
    install -Dm 0755 -o galaxy /app/docker/bin/* /usr/local/bin/ && \
    install -Dm 0775 -o galaxy /app/galaxy-operator/bin/* /usr/bin/

USER galaxy
VOLUME [ "/var/lib/pulp", \
         "/etc/pulp", \
         "/tmp/ansible" ]
ENTRYPOINT [ "/entrypoint.sh" ]
