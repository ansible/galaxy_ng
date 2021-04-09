#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

readonly WITH_MIGRATIONS="${WITH_MIGRATIONS:-0}"
readonly WITH_DEV_INSTALL="${WITH_DEV_INSTALL:-0}"
readonly DEV_SOURCE_PATH="${DEV_SOURCE_PATH:-}"
readonly LOCK_REQUIREMENTS="${LOCK_REQUIREMENTS:-1}"


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

    wait-for-tcp "${PULP_DB_HOST:-localhost}" "${PULP_DB_PORT:-5432}"
    wait-for-tcp "${PULP_REDIS_HOST:-localhost}" "${PULP_REDIS_PORT:-6379}"

    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi

    if [[ "${WITH_MIGRATIONS}" -eq "1" ]]; then
        django-admin migrate
    else
        wait-for-migrations
    fi

    process_init_files /entrypoints.d/*

    exec "${service_path}" "$@"
}


run_manage() {
    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi
    exec django-admin "$@"
}


redis_connection_hack() {
    if [[ "$PULP_REDIS_SSL" == "true" ]]; then
        protocol="rediss://"
    else
        protocol="redis://"
    fi

    if [[ -z "$PULP_REDIS_PASSWORD" ]]; then
        password=""
    else
        password=":${PULP_REDIS_PASSWORD}@"
    fi

    PULP_REDIS_URL="${protocol}${password}${PULP_REDIS_HOST:-localhost}:${PULP_REDIS_PORT:-6379}/0"
    unset PULP_REDIS_HOST PULP_REDIS_PORT PULP_REDIS_PASSWORD
    export PULP_REDIS_URL
}

main() {
    if [[ "$#" -eq 0 ]]; then
        exec "/bin/bash"
    fi

    # TODO: remove once Pulp recognizes REDIS_SSL parameter when building settings for RQ in pulpcore/rqconfig.py
    redis_connection_hack

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
