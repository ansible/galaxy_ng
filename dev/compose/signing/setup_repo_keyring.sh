#!/usr/bin/env bash
set -o errexit
set -o pipefail

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --keyring /etc/pulp/gnupg/pubring.kbx -y;
done

