# #!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

source /app/profiles/base/init.sh

cp -r /app/profiles/community/galaxy-importer /etc/galaxy-importer

setup_collection_signing_service

# collect rest_framewrok static files
django-admin collectstatic --no-input --clear
