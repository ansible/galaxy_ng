#!/usr/bin/env bash

MANIFEST_PATH=$1
HOME=$(cat /etc/pulp/certs/HOME.workaround.txt)

skopeo standalone-sign \
    --passphrase-file /etc/pulp/certs/signing-secret.key.password.txt \
    --output $SIG_PATH \
    $MANIFEST_PATH $REFERENCE $PULP_SIGNING_KEY_FINGERPRINT

[ $? -eq 0 ] && echo {\"signature_path\": \"$SIG_PATH\"} || exit $?
