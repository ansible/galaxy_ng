#!/bin/bash

set -o errexit
set -o nounset
set -o verbose


readonly DOCKER_CONF="${PWD}/.docker"
readonly IMAGE='quay.io/cloudservices/automation-hub-galaxy-ng'
readonly IMAGE_TAG="$(git rev-parse --short=7 HEAD)"

readonly QUAY_USER="${QUAY_USER:-}"
readonly QUAY_TOKEN="${QUAY_TOKEN:-}"

readonly RH_REGISTRY_USER="${RH_REGISTRY_USER:-}"
readonly RH_REGISTRY_TOKEN="${RH_REGISTRY_TOKEN:-}"

if [[ "${GIT_BRANCH}" == 'stable' ]]; then
    IMAGE_ALIAS='qa'
else
    IMAGE_ALIAS='latest'
fi

if [[ -z "${QUAY_USER}" || -z "${QUAY_TOKEN}" ]]; then
    echo "Error: QUAY_USER and QUAY_TOKEN must be set."
    exit 1
fi

if [[ -z "${RH_REGISTRY_USER}" || -z "${RH_REGISTRY_TOKEN}" ]]; then
    echo "Error: RH_REGISTRY_USER and RH_REGISTRY_TOKEN must be set."
    exit 1
fi

mkdir -p "${DOCKER_CONF}"

docker --config="${DOCKER_CONF}" login --username "${QUAY_USER}" --password "${QUAY_TOKEN}" quay.io
docker --config="${DOCKER_CONF}" login --username "${RH_REGISTRY_USER}" --password "${RH_REGISTRY_TOKEN}" registry.redhat.io
docker --config="${DOCKER_CONF}" build --tag "${IMAGE}:${IMAGE_TAG}" .
docker --config="${DOCKER_CONF}" push "${IMAGE}:${IMAGE_TAG}"

docker --config="${DOCKER_CONF}" tag "${IMAGE}:${IMAGE_TAG}" "${IMAGE}:${IMAGE_ALIAS}"
docker --config="${DOCKER_CONF}" push "${IMAGE}:${IMAGE_ALIAS}"
