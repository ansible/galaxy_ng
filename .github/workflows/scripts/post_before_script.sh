#!/usr/bin/env bash

set -mveuo pipefail
shopt -s expand_aliases
source .github/workflows/scripts/utils.sh
cmd_prefix bash -c "django-admin compilemessages"

echo "machine pulp
login admin
password password
" > ~pulp/.netrc

chmod og-rw ~pulp/.netrc
