#!/usr/bin/env bash

set -mveuo pipefail
source .github/workflows/scripts/utils.sh
cmd_prefix bash -c "django-admin compilemessages"


cmd_stdin_prefix bash -c "cat > /var/lib/pulp/sign-metadata.sh" < "$GITHUB_WORKSPACE"/galaxy_ng/tests/assets/sign-metadata.sh

cmd_prefix bash -c "curl -L https://github.com/pulp/pulp-fixtures/raw/master/common/GPG-PRIVATE-KEY-pulp-qe | gpg --import"
cmd_prefix bash -c "curl -L https://github.com/pulp/pulp-fixtures/raw/master/common/GPG-KEY-pulp-qe | cat > /tmp/GPG-KEY-pulp-qe"
cmd_prefix chmod a+x /var/lib/pulp/sign-metadata.sh

KEY_FINGERPRINT="6EDF301256480B9B801EBA3D05A5E6DA269D9D98"
TRUST_LEVEL="6"
echo "$KEY_FINGERPRINT:$TRUST_LEVEL:" | cmd_stdin_prefix gpg --import-ownertrust

echo "machine pulp
login admin
password password
" > ~/.netrc

chmod og-rw ~/.netrc
