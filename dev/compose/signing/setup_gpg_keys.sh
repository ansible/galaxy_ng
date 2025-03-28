#!/usr/bin/env bash
set -o errexit
set -o pipefail

# ensure agent is running
gpgconf --kill gpg-agent

DB_ENCRYPTION_KEY=${DB_ENCRYPTION_KEY:-"/etc/pulp/certs/signing-secret.key"}

# Import the key
gpg --batch --no-default-keyring --import ${DB_ENCRYPTION_KEY};

# Set the key trust level
(echo 5; echo y; echo save) | gpg --command-fd 0 --no-tty --no-greeting -q --edit-key 'FB8B3F2D24BCAF7EFDF793A9F37575C52D4F16F3' trust;
