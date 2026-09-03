#!/usr/bin/env bash
set -o errexit
set -o pipefail

FILE="$1"
# Dedicated post-quantum sq (Sequoia PGP) dev key (ML-DSA-65+Ed25519, RFC9580),
# separate from the gpg `ansible-default` key. `sq sign` auto-selects the
# signing-capable subkey from the file. Unencrypted for dev.
SECRET_KEY=/etc/pulp/certs/signing-secret-sq.key

sq --batch --home /etc/pulp/certs/sequoia \
    sign \
    --signer-file "$SECRET_KEY" \
    --signature-file "${FILE}.asc" \
    "$FILE"

[ $? -eq 0 ] && echo {\"file\": \"$FILE\", \"signature\": \"$FILE.asc\"} || exit $?
