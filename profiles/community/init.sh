# #!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

source /src/galaxy_ng/profiles/base/init.sh

setup_collection_signing_service

# collect rest_framewrok static files
django-admin collectstatic --no-input --clear
