#!/usr/bin/env bash

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --keyring /root/.gnupg/pubring.kbx -y;
done

