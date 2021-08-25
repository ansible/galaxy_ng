#!/usr/bin/env bash

set -mveuo pipefail
source .github/workflows/scripts/utils.sh
cmd_prefix bash -c "django-admin compilemessages"