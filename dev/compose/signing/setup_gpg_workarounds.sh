#!/usr/bin/env bash
DEFAULT_GNUPGHOME="$HOME/.gnupg"
CURRENT_GNUPGHOME="${GNUPGHOME:-$DEFAULT_GNUPGHOME}"

# Remove both `.gnupg` and potential trailing `/` after `.gnupg`
CURRENT_HOME="${CURRENT_GNUPGHOME%/.gnupg/}"
CURRENT_HOME="${CURRENT_HOME%/.gnupg}"

echo "$CURRENT_GNUPGHOME" > /etc/pulp/certs/GNUPGHOME.workaround.txt
echo "$CURRENT_HOME" > /etc/pulp/certs/HOME.workaround.txt
