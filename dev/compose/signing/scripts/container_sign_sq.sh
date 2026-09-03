#!/usr/bin/env bash
set -o errexit
set -o pipefail

# PQC (ML-DSA) container / execution-environment manifest signing with sq
# (Sequoia PGP). skopeo standalone-sign uses gpg, which has no post-quantum
# support, so we build the containers/image "simple signing" (atomic) payload
# ourselves and sign it inline with sq. pulp_container parses the inline signed
# message via pysequoia (extract_data_from_signature), which understands ML-DSA.
MANIFEST_PATH="$1"
SECRET_KEY=/etc/pulp/certs/signing-secret-sq.key

DIGEST="sha256:$(sha256sum "$MANIFEST_PATH" | awk '{print $1}')"

# $REFERENCE and $SIG_PATH are supplied by pulp when invoking the service.
PAYLOAD_FILE=$(mktemp)
cat > "$PAYLOAD_FILE" <<EOF
{"critical":{"identity":{"docker-reference":"${REFERENCE}"},"image":{"docker-manifest-digest":"${DIGEST}"},"type":"atomic container signature"},"optional":{"creator":"galaxy_ng dev sq","timestamp":$(date +%s)}}
EOF

sq --batch --home /etc/pulp/certs/sequoia \
    sign --message \
    --signer-file "$SECRET_KEY" \
    --output "$SIG_PATH" \
    "$PAYLOAD_FILE"

rm -f "$PAYLOAD_FILE"

echo {\"signature_path\": \"$SIG_PATH\"}
