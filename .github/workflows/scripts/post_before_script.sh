#!/usr/bin/env bash

set -mveuo pipefail
source .github/workflows/scripts/utils.sh
cmd_prefix bash -c "django-admin compilemessages"

echo "machine pulp
login admin
password password
" > ~/.netrc

chmod og-rw ~/.netrc
