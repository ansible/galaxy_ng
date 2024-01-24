#!/bin/bash -eu

/usr/bin/wait_on_postgres.py
/usr/local/bin/wait-for-migrations

if [ -n "${PULP_SIGNING_KEY_FINGERPRINT}" ]; then
  /usr/local/bin/pulpcore-manager add-signing-service "${COLLECTION_SIGNING_SERVICE}" /app/dev/common/collection_sign.sh "${PULP_SIGNING_KEY_FINGERPRINT}"
  /usr/local/bin/pulpcore-manager add-signing-service "${CONTAINER_SIGNING_SERVICE}" /app/dev/common/container_sign.sh "${PULP_SIGNING_KEY_FINGERPRINT}" --class container:ManifestSigningService
fi
