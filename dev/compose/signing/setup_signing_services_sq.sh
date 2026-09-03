#!/usr/bin/env bash
set -o errexit
set -o pipefail

# Additional signing service that signs collections with the `sq` (Sequoia PGP)
# CLI instead of gpg. Registered alongside the gpg-based `ansible-default`.
# Uses a dedicated post-quantum (ML-DSA-65+Ed25519, RFC9580/v6) key so its
# signatures are distinguishable from the gpg key's and exercise the PQC path.
# v6 fingerprints are 256-bit (64 hex chars).
SQ_FINGERPRINT=A02C49E9A3C0F634A4752547750097BF3F84122B8C1114684E56B5ACE7817CD9

# Collection
HAS_COLLECTION_SIGNING_SQ=$(pulpcore-manager shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="ansible-sq").count())' 2>/dev/null || true)
if [[ "$HAS_COLLECTION_SIGNING_SQ" -eq "0" ]]; then
    pulpcore-manager add-signing-service ansible-sq /var/lib/pulp/scripts/collection_sign_sq.sh "$SQ_FINGERPRINT" \
        --backend sq --keyring /etc/pulp/certs/signing-public-sq.key --home /etc/pulp/certs/sequoia
else
    echo "Collection Signing Service (sq) Already exists"
fi

# Container / execution environment (PQC equivalent of container-default)
HAS_CONTAINER_SIGNING_SQ=$(pulpcore-manager shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="container-sq").count())' 2>/dev/null || true)
if [[ "$HAS_CONTAINER_SIGNING_SQ" -eq "0" ]]; then
    pulpcore-manager add-signing-service container-sq /var/lib/pulp/scripts/container_sign_sq.sh "$SQ_FINGERPRINT" \
        --backend sq --class container:ManifestSigningService \
        --keyring /etc/pulp/certs/signing-public-sq.key --home /etc/pulp/certs/sequoia
else
    echo "Container Signing Service (sq) Already exists"
fi
