#!/bin/bash

set -e

# if [ ! grep -Fxq "SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY" /etc/pulp/settings.py ]
# then
#     echo "Keycloak already initialized."
#     exit 0
# elif

# intialize keycloak
ansible-galaxy collection install /src/galaxy_ng/profiles/keycloak/community-general-5.7.0.tar.gz
ansible-playbook /src/galaxy_ng/profiles/keycloak/keycloak-playbook.yaml

# Restart pulp services so that settings are reloaded
SERVICES=$(s6-rc -a list | grep -E ^pulp)
echo "$SERVICES" | xargs -I {} s6-rc -d change {}
echo "$SERVICES" | xargs -I {} s6-rc -u change {}
s6-rc -u change nginx
