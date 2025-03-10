#!/usr/bin/env bash
GNUPGHOME=$(cat /etc/pulp/certs/GNUPGHOME.workaround.txt)

gpg --lock-never \
    --quiet \
    --batch \
    --pinentry-mode loopback \
    --yes \
    --passphrase $(cat /etc/pulp/certs/signing-secret.key.password.txt) \
    --homedir "$GNUPGHOME" \
    --detach-sign \
    --default-key $PULP_SIGNING_KEY_FINGERPRINT \
    --armor \
    --output $1.asc \
    $1

[ $? -eq 0 ] && echo {\"file\": \"$1\", \"signature\": \"$1.asc\"} || exit $?
