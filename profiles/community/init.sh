# #!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

cp -r /src/galaxy_ng/profiles/community/galaxy-importer /etc/galaxy-importer

setup_collection_signing_service

# collect rest_framewrok static files
django-admin collectstatic --no-input --clear
