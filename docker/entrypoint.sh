#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

readonly WITH_MIGRATIONS="${WITH_MIGRATIONS:-0}"
readonly WITH_DEV_INSTALL="${WITH_DEV_INSTALL:-0}"
readonly DEV_SOURCE_PATH="${DEV_SOURCE_PATH:-}"
readonly LOCK_REQUIREMENTS="${LOCK_REQUIREMENTS:-1}"
readonly WAIT_FOR_MIGRATIONS="${WAIT_FOR_MIGRATIONS:-0}"


log_message() {
    echo "$@" >&2
}

setup_signing_service() {
    log_message "Setting up signing service"
    # this assumes the key file is mounted during container startup time.
    # the dev environment key was created using `galaxy3@ansible.com` admin ID
    gpg --batch --import /tmp/ansible-sign.key &>/dev/null
    # Pulp AsciiArmoured default SS expects a higher trust level so we need to edit it after import
    (echo trust &echo 5 &echo y &echo quit &echo save) | gpg --batch --command-fd 0 --edit-key galaxy3 &>/dev/null

    # Add the signing service using pulp command, this assumes the script is mounted during container startup
    HAS_SIGNING=$(django-admin shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="ansible-default").count())' 2>/dev/null || true)
    if [[ "$HAS_SIGNING" -eq "1" ]]; then
        log_message "Signing service already exists"
    else
        log_message "Creating signing service"
        django-admin add-signing-service ansible-default /var/lib/pulp/scripts/collection_sign.sh galaxy3@ansible.com 2>/dev/null || true
    fi

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
                pip install --no-cache-dir --no-deps --editable "$src_path" >/dev/null
            else
                pip install --no-cache-dir --editable "$src_path" >/dev/null
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

    setup_signing_service

    exec "${service_path}" "$@"
}


run_manage() {
    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi

    setup_signing_service
    exec django-admin "$@"
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
