#!/usr/bin/env bash
set -o errexit
set -o pipefail

PUBLIC_KEY=/etc/pulp/gnupg/pubring.kbx

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --keyring $PUBLIC_KEY -y;
done

