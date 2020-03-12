#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail


_wait_tcp_port() {
  local -r host="$1"
  local -r port="$2"

  local attempts=6
  local timeout=1

  echo "[debug]: Waiting for port tcp://${host}:${port}"
  while [ $attempts -gt 0 ]; do
    timeout 1 /bin/bash -c ">/dev/tcp/${host}/${port}" &>/dev/null && return 0 || :

    echo "[debug]: Waiting ${timeout} seconds more..."
    sleep $timeout

    timeout=$(( $timeout * 2 ))
    attempts=$(( $attempts - 1 ))
  done

  echo "[error]: Port tcp://${host}:${port} is not available"
  return 1
}

run_service() {
  if [[ "$#" -eq 0 ]]; then
    echo '[error]: Missing service name parameter.' >&2
    exit 1
  fi

  service_name="$1"; shift
  service_path="/usr/local/bin/start-${service_name}.sh"

  if [[ ! -x "${service_path}" ]]; then
    echo "[error]: Unable to execute service '${service_name}'." >&2
    exit 1
  fi

  _wait_tcp_port "${PULP_DB_HOST:-localhost}" "${PULP_DB_PORT:-5432}"
  pip install --no-deps --editable "/app" >/dev/null
  django-admin migrate

  exec "${service_path}" "$@"
}

run_manage() {
  pip install --no-deps --editable "/app" >/dev/null
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
