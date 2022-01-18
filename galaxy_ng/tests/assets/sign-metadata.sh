#!/usr/bin/env bash

FILE_PATH=$1
SIGNATURE_PATH="$1.asc"

GPG_KEY_ID="Pulp QE"

# Create a detached signature
gpg --quiet --batch --homedir ~/.gnupg/ --detach-sign --local-user "${GPG_KEY_ID}" \
   --armor --output ${SIGNATURE_PATH} ${FILE_PATH}

# Check the exit status
STATUS=$?
if [[ ${STATUS} -eq 0 ]]; then
   echo {\"file\": \"${FILE_PATH}\", \"signature\": \"${SIGNATURE_PATH}\"}
else
   exit ${STATUS}
fi