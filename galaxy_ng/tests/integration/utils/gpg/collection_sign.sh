#!/usr/bin/env bash

FILE_PATH=$1
SIGNATURE_PATH="$1.asc"

ADMIN_ID="galaxy3@ansible.com"
PASSWORD="Galaxy2022"

# Create a detached signature
gpg --debug-all --lock-never --quiet --batch --pinentry-mode loopback --yes --passphrase \
   $PASSWORD --homedir ~/.gnupg/ --detach-sign --default-key $ADMIN_ID \
   --no-default-keyring --keyring ${KEYRING:-/etc/pulp/certs/galaxy.kbx} \
   --armor --output $SIGNATURE_PATH $FILE_PATH

# Check the exit status
STATUS=$?
if [ $STATUS -eq 0 ]; then
   echo {\"file\": \"$FILE_PATH\", \"signature\": \"$SIGNATURE_PATH\"}
else
   exit $STATUS
fi
