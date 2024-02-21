#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

readonly WITH_MIGRATIONS="${WITH_MIGRATIONS:-0}"
readonly WITH_DEV_INSTALL="${WITH_DEV_INSTALL:-0}"
readonly DEV_SOURCE_PATH="${DEV_SOURCE_PATH:-}"
readonly LOCK_REQUIREMENTS="${LOCK_REQUIREMENTS:-1}"
readonly WAIT_FOR_MIGRATIONS="${WAIT_FOR_MIGRATIONS:-0}"
readonly ENABLE_SIGNING="${ENABLE_SIGNING:-0}"
readonly PULP_GALAXY_DEPLOYMENT_MODE="${PULP_GALAXY_DEPLOYMENT_MODE:-}"


log_message() {
    echo "$@" >&2
}

# TODO(cutwater): This function should be moved to entrypoint hooks.
install_local_deps() {
    local src_path_list
    IFS=':' read -ra src_path_list <<< "$DEV_SOURCE_PATH"

    for item in "${src_path_list[@]}"; do
        src_path="/src/${item}"
        if [[ -d "$src_path" ]]; then
            log_message "Installing path ${item} in editable mode."

            if [[ "${LOCK_REQUIREMENTS}" -eq "1" ]]; then
                pip3.11 install --no-cache-dir --no-deps --editable "$src_path" >/dev/null
            else
                pip3.11 install --no-cache-dir --editable "$src_path" >/dev/null
            fi

        else
            log_message "WARNING: Source path ${item} is not a directory."
        fi
    done
}

process_init_files() {
    local file
    for file; do
        case "$file" in
            *.sh)
                if [[ -x "$file" ]]; then
                    log_message "$0: running $file"
                    "$file"
                else
                    log_message "$0: sourcing $file"
                    source "$file"
                fi
                ;;
            *) log_message "$0: ignoring $file" ;;
        esac
    done
}

run_service() {
    if [[ "$#" -eq 0 ]]; then
        log_message 'ERROR: Missing service name parameter.'
        exit 1
    fi

    service_name="$1"; shift
    service_path="/usr/local/bin/start-${service_name}"

    if [[ ! -x "${service_path}" ]]; then
        log_message "ERROR: Unable to execute service '${service_name}'."
        exit 1
    fi

    # wait-for-tcp "${PULP_DB_HOST:-localhost}" "${PULP_DB_PORT:-5432}"
    # wait-for-tcp "${PULP_REDIS_HOST:-localhost}" "${PULP_REDIS_PORT:-6379}"

    # TODO: remove once Pulp recognizes REDIS_SSL parameter when building
    # settings for RQ in pulpcore/rqconfig.py
    redis_connection_hack

    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi

    if [[ "${WITH_MIGRATIONS}" -eq "1" ]]; then
        django-admin migrate
    elif [[ "${WAIT_FOR_MIGRATIONS}" -eq "1" ]]; then
        wait-for-migrations
    fi

    process_init_files /entrypoints.d/*

    if [[ "$PULP_GALAXY_DEPLOYMENT_MODE" = "insights" ]]; then
        django-admin maintain-pe-group
    fi

    if [[ "$ENABLE_SIGNING" -eq "1" ]]; then
        setup_signing_keyring
        setup_repo_keyring &
        setup_collection_signing_service & 
        setup_container_signing_service
    elif [[ "$ENABLE_SIGNING" -eq "2" ]]; then
        setup_signing_keyring
        setup_repo_keyring &
    fi

    exec "${service_path}" "$@"
}


run_manage() {
    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi

    if [[ "$ENABLE_SIGNING" -eq "1" ]]; then
        setup_signing_keyring
        setup_collection_signing_service &
        setup_container_signing_service
    elif [[ "$ENABLE_SIGNING" -eq "2" ]]; then
        setup_signing_keyring
    fi

    exec django-admin "$@"
}

setup_signing_keyring() {
    log_message "Setting up signing keyring."
    for KEY_FINGERPRINT in $(gpg --show-keys --with-colons --with-fingerprint /tmp/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}')
    do
        gpg --batch --no-default-keyring --keyring /etc/pulp/certs/galaxy.kbx --import /tmp/ansible-sign.key &>/dev/null
        echo "${KEY_FINGERPRINT}:6:" | gpg --batch --no-default-keyring --keyring /etc/pulp/certs/galaxy.kbx --import-ownertrust &>/dev/null
    done
}

setup_repo_keyring() {
    # run after a short delay, otherwise the django-admin command hangs
    sleep 30
    STAGING_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='staging').keyring)" 2>/dev/null || true)
    if [[ "${STAGING_KEYRING}" != "/etc/pulp/certs/galaxy.kbx" ]]; then
        log_message "Setting keyring for staging repo"
        django-admin set-repo-keyring --repository staging --keyring /etc/pulp/certs/galaxy.kbx -y
    else
        log_message "Keyring is already set for staging repo."
    fi
    PUBLISHED_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='published').keyring)" 2>/dev/null || true)
    if [[ "${PUBLISHED_KEYRING}" != "/etc/pulp/certs/galaxy.kbx" ]]; then
        log_message "Setting keyring for published repo"
        django-admin set-repo-keyring --repository published --keyring /etc/pulp/certs/galaxy.kbx -y
    else
        log_message "Keyring is already set for published repo."
    fi
}

setup_collection_signing_service() {
    log_message "Setting up collection signing service."
    export KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint /tmp/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}' | head -n1)
    export KEY_ID=${KEY_FINGERPRINT: -16}
    gpg --batch --import /tmp/ansible-sign.key &>/dev/null
    echo "${KEY_FINGERPRINT}:6:" | gpg --import-ownertrust &>/dev/null

    HAS_SIGNING=$(django-admin shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="ansible-default").count())' 2>/dev/null || true)
    if [[ "$HAS_SIGNING" -eq "0" ]]; then
        log_message "Creating signing service. using key ${KEY_ID}"
        django-admin add-signing-service ansible-default /var/lib/pulp/scripts/collection_sign.sh ${KEY_ID} 2>/dev/null || true
    else
        log_message "Signing service already exists."
    fi

}

setup_container_signing_service() {

    if ! skopeo --version > /dev/null; then
        log_message 'WARNING: skopeo is not installed. Skipping container signing service setup.'
        return
    fi

    log_message "Setting up container signing service."
    export KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint /tmp/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}' | head -n1)
    export KEY_ID=${KEY_FINGERPRINT: -16}
    gpg --batch --import /tmp/ansible-sign.key &>/dev/null
    echo "${KEY_FINGERPRINT}:6:" | gpg --import-ownertrust &>/dev/null

    HAS_CONTAINER_SIGNING=$(django-admin shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="container-default").count())' 2>/dev/null || true)
    if [[ "$HAS_CONTAINER_SIGNING" -eq "0" ]]; then
        log_message "Creating container signing service. using key ${KEY_ID}"
        django-admin add-signing-service container-default /var/lib/pulp/scripts/container_sign.sh ${KEY_ID} --class container:ManifestSigningService 2>/dev/null || true
    else
        log_message "Container signing service already exists."
    fi
}

redis_connection_hack() {
    redis_host="${PULP_REDIS_HOST:-}"
    redis_password="${PULP_REDIS_PASSWORD:-}"
    redis_port="${PULP_REDIS_PORT:-}"
    redis_ssl="${PULP_REDIS_SSL:-}"

    if [[ -z "${redis_host}" && -z "${redis_port}" &&
          -z "${redis_password}" ]]; then
        return
    fi

    if [[ "${redis_ssl}" == "true" ]]; then
        protocol="rediss://"
    else
        protocol="redis://"
    fi

    if [[ -n "${redis_password}" ]]; then
        password=":${redis_password}@"
    else
        password=""
    fi

    PULP_REDIS_URL="${protocol}${password}${redis_host}:${redis_port:-6379}/0"
    unset PULP_REDIS_HOST PULP_REDIS_PORT PULP_REDIS_PASSWORD
    export PULP_REDIS_URL
}

main() {
    if [[ "$#" -eq 0 ]]; then
        exec "/bin/bash"
    fi

    case "$1" in
        'run')
            run_service "${@:2}"
            ;;
        'manage')
            run_manage "${@:2}"
            ;;
        *)
            exec "$@"
            ;;
    esac
}


main "$@"
