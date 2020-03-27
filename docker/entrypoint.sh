#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail


readonly WITH_MIGRATIONS="${WITH_MIGRATIONS:-0}"
readonly WITH_DEV_INSTALL="${WITH_DEV_INSTALL:-0}"


log_message() {
    echo "$@" >&2
}


install_local_deps() {
    pip install --no-cache --no-deps --editable "/app" >/dev/null
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

    exec "${service_path}" "$@"
}


run_manage() {
    if [[ "$WITH_DEV_INSTALL" -eq "1" ]]; then
        install_local_deps
    fi
    exec django-admin "$@"
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
