#!/bin/bash

set -o errexit
set -o nounset


readonly WORKER_CLASS='pulpcore.tasking.worker.PulpWorker'
readonly WORKER_CONFIG='pulpcore.rqconfig'


exec rq worker -w "${WORKER_CLASS}" -c "${WORKER_CONFIG}"
