#!/usr/bin/env bash
set -o errexit
set -o pipefail

PUBLIC_KEY=/etc/pulp/certs/signing-public.key
TEST_PUBLIC_KEY=/src/galaxy_ng/dev/common/ansible-sign-pub.gpg

# Build a combined keyring containing both the server signing key and the
# test signing key so that uploaded signatures (signed with either key) can
# be verified.
COMBINED_KEY=$(mktemp)
cat "$PUBLIC_KEY" > "$COMBINED_KEY"
if [ -f "$TEST_PUBLIC_KEY" ]; then
    cat "$TEST_PUBLIC_KEY" >> "$COMBINED_KEY"
fi

for repo in staging published; do
    pulpcore-manager set-repo-keyring --repository $repo --publickeypath "$COMBINED_KEY" -y;
done

rm -f "$COMBINED_KEY"

