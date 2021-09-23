#!/usr/bin/env bash

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

set -mveuo pipefail

# Replacing ngix conf
rm galaxy_ng/app/webserver_snippets/nginx.conf
mv .ci/assets/nginx/nginx.conf galaxy_ng/app/webserver_snippets/nginx.conf
