#!/bin/bash


cat /etc/pulp/settings.py | grep -q SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY

STATUS=$?
if [ $STATUS -eq 0 ]; then
   echo "Keycloak already configured"
   exit 0
fi

set -e

# intialize keycloak
ansible-galaxy collection install /src/galaxy_ng/profiles/keycloak/community-general-5.7.0.tar.gz
ansible-playbook /src/galaxy_ng/profiles/keycloak/keycloak-playbook.yaml

# Restart pulp services so that settings are reloaded
SERVICES=$(s6-rc -a list | grep -E ^pulp)
echo "$SERVICES" | xargs -I {} s6-rc -d change {}
echo "$SERVICES" | xargs -I {} s6-rc -u change {}
s6-rc -u change nginx
