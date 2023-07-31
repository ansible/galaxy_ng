# #!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

source /src/galaxy_ng/profiles/base/init.sh

cp -r /src/galaxy_ng/profiles/community/galaxy-importer /etc/galaxy-importer

setup_collection_signing_service

# collect rest_framewrok static files
django-admin collectstatic --no-input --clear
