#!/usr/bin/env bash
set -o errexit
set -o pipefail

# Collection
HAS_COLLECTION_SIGNING=$(pulpcore-manager shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="ansible-default").count())' 2>/dev/null || true)
if [[ "$HAS_COLLECTION_SIGNING" -eq "0" ]]; then
    pulpcore-manager add-signing-service ansible-default /var/lib/pulp/scripts/collection_sign.sh F37575C52D4F16F3
else
    echo "Collection Signing Service Already exists"
fi

# Container
HAS_CONTAINER_SIGNING=$(pulpcore-manager shell -c 'from pulpcore.app.models import SigningService;print(SigningService.objects.filter(name="container-default").count())' 2>/dev/null || true)
if [[ "$HAS_CONTAINER_SIGNING" -eq "0" ]]; then
    pulpcore-manager add-signing-service container-default /var/lib/pulp/scripts/container_sign.sh F37575C52D4F16F3 --class container:ManifestSigningService
else
    echo "Container Signing Service Already exists"
fi
