#!/usr/bin/env bash

# This GPG_TTY variable might be needed on a container image that is not running as root.
#export GPG_TTY=$(tty)

# On a production system, this next variable should be set on the outer environment, not here.
# export PULP_CONTAINER_SIGNING_KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint /tmp/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}' | head -n1)
# Below matches the fingerprint for dev environment key.
export PULP_CONTAINER_SIGNING_KEY_FINGERPRINT=EBED170E8C9480E22A1D059B15250E9EC0A62577

# Create a file with passphrase only if the key is password protected.
echo "Galaxy2022" > /tmp/key_password.txt

# pulp_container SigningService will pass the next 3 variables to the script.
MANIFEST_PATH=$1
IMAGE_REFERENCE="$REFERENCE"
SIGNATURE_PATH="$SIG_PATH"

# Create container signature using skopeo
# omit --passphrase-file option if the key is not password protected.
skopeo standalone-sign \
  --passphrase-file /tmp/key_password.txt \
  $MANIFEST_PATH \
  $IMAGE_REFERENCE \
  $PULP_CONTAINER_SIGNING_KEY_FINGERPRINT \
  --output $SIGNATURE_PATH

# Check the exit status
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo {\"signature_path\": \"$SIGNATURE_PATH\"}
else
  exit $STATUS
fi
