#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

readonly ENABLE_SIGNING="${ENABLE_SIGNING:-0}"

log_message() {
    echo "$@" >&2
}

setup_signing_keyring() {
    log_message "Setting up signing keyring."
    for KEY_FINGERPRINT in $(gpg --show-keys --with-colons --with-fingerprint /src/galaxy_ng/dev/common/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}')
    do
        gpg --batch --no-default-keyring --keyring /etc/pulp/certs/galaxy.kbx --import /src/galaxy_ng/dev/common/ansible-sign.key
        echo "${KEY_FINGERPRINT}:6:" | gpg --batch --no-default-keyring --keyring /etc/pulp/certs/galaxy.kbx --import-ownertrust
    done
}

setup_repo_keyring() {
    # run after a short delay, otherwise the django-admin command hangs
    sleep 30
    STAGING_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='staging').keyring)" || true)
    if [[ "${STAGING_KEYRING}" != "/etc/pulp/certs/galaxy.kbx" ]]; then
        log_message "Setting keyring for staging repo"
        django-admin set-repo-keyring --repository staging --keyring /etc/pulp/certs/galaxy.kbx -y
    else
        log_message "Keyring is already set for staging repo."
    fi
    PUBLISHED_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='published').keyring)" || true)
    if [[ "${PUBLISHED_KEYRING}" != "/etc/pulp/certs/galaxy.kbx" ]]; then
        log_message "Setting keyring for published repo"
        django-admin set-repo-keyring --repository published --keyring /etc/pulp/certs/galaxy.kbx -y
    else
        log_message "Keyring is already set for published repo."
    fi
}

setup_collection_signing_service() {
    log_message "Setting up signing service."
    export KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint /src/galaxy_ng/dev/common/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}' | head -n1)
    export KEY_ID=${KEY_FINGERPRINT: -16}
    gpg --batch --import /src/galaxy_ng/dev/common/ansible-sign.key
    echo "${KEY_FINGERPRINT}:6:" | gpg --import-ownertrust

    HAS_SIGNING=$(django-admin shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="ansible-default").count())' || true)
    if [[ "$HAS_SIGNING" -eq "0" ]]; then
        log_message "Creating signing service. using key ${KEY_ID}"
        django-admin add-signing-service ansible-default /src/galaxy_ng/dev/common/collection_sign.sh ${KEY_ID}  || true
    else
        log_message "Signing service already exists."
    fi
}

setup_container_signing_service() {

    if ! skopeo --version > /dev/null; then
        log_message 'WARNING: skopeo is not installed. Skipping container signing service setup.'
        return
    fi

    log_message "Setting up container signing service."
    export KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint /src/galaxy_ng/dev/common/ansible-sign.key | awk -F: '$1 == "fpr" {print $10;}' | head -n1)
    export KEY_ID=${KEY_FINGERPRINT: -16}
    gpg --batch --import /src/galaxy_ng/dev/common/ansible-sign.key
    echo "${KEY_FINGERPRINT}:6:" | gpg --import-ownertrust

    HAS_CONTAINER_SIGNING=$(django-admin shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="container-default").count())' || true)
    if [[ "$HAS_CONTAINER_SIGNING" -eq "0" ]]; then
        log_message "Creating container signing service. using key ${KEY_ID}"
        django-admin add-signing-service container-default /src/galaxy_ng/dev/common/container_sign.sh ${KEY_ID} --class container:ManifestSigningService || true
    else
        log_message "Container signing service already exists."
    fi
}

if [[ "$ENABLE_SIGNING" -eq "1" ]]; then
    setup_signing_keyring
    setup_repo_keyring &
    setup_collection_signing_service &
    setup_container_signing_service
elif [[ "$ENABLE_SIGNING" -eq "2" ]]; then
    setup_signing_keyring
    setup_repo_keyring &
fi
