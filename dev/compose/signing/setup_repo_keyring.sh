#!/usr/bin/env bash
PUBLIC_KEY=/root/.gnupg/pubring.kbx

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --keyring $PUBLIC_KEY -y;
done

