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
    log_message "Setting up repository keyrings"
    STAGING_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='staging').gpgkey)" || true)
    if [[ "${STAGING_KEYRING}" != "/etc/pulp/certs/galaxy.kbx" ]]; then
        log_message "Setting keyring for staging repo"
        django-admin set-repo-keyring --repository staging --keyring /etc/pulp/certs/galaxy.kbx -y
    else
        log_message "Keyring is already set for staging repo."
    fi
    PUBLISHED_KEYRING=$(django-admin shell -c "from pulp_ansible.app.models import AnsibleRepository;print(AnsibleRepository.objects.get(name='published').gpgkey)" || true)
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
        django-admin add-signing-service ansible-default /src/galaxy_ng/dev/common/collection_sign.sh ${KEY_ID} || true
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

set_pulp_user_perms() {
    # This is a hack to make the signing service work with the new pulp user. Basically, this script gets run as
    # root, which causes the .gnugpg keyring to get created under the /root/.gnugpg/ directory. This directory
    # isn't accessible to the pulp workers or signing script, so it has to be copied over into the pulp user's dir
    # (/var/lib/pulp).
    # A keen eye'd observer might ask "why don't you just set GNUGPGHOME here to the pulp user's home dir instead of 
    # copying this over from the root home dir?" As it turns out, that doesn't work because "django-admin add-signing-service"
    # attempts to validate the signing service by creating a temporary file and signing it. This fails because the django-admin
    # command will attemt to load the gpg home dir from the user that's running the django-admin command (in this case root)
    # and not the user that pulp is running under (in this case pulp), which will cause the validation to fail.
    cp -r /root/.gnupg /var/lib/pulp/.gnupg

    chown -R pulp:pulp /var/lib/pulp/.gnupg
    chown -R pulp:pulp /etc/pulp/certs/galaxy.kbx
}

download_ui() {
    # download the latest version of the UI from github
    python3 /src/galaxy_ng/setup.py prepare_static --force-download-ui
    echo "yes" | django-admin collectstatic
}


if [[ "$ENABLE_SIGNING" -eq "1" ]]; then
    setup_signing_keyring
    setup_repo_keyring &
    setup_collection_signing_service &
    setup_container_signing_service
    set_pulp_user_perms
elif [[ "$ENABLE_SIGNING" -eq "2" ]]; then
    setup_signing_keyring
    setup_repo_keyring &
    set_pulp_user_perms
fi

download_ui