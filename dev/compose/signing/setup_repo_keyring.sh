#!/usr/bin/env bash
set -o errexit
set -o pipefail

PUBLIC_KEY=/etc/pulp/certs/signing-public.key

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --publickeypath $PUBLIC_KEY -y;
done

