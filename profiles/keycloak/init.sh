#!/bin/bash


set -x
export S6_VERBOSITY=2


cat /etc/pulp/settings.py | grep -q SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY

STATUS=$?
if [ $STATUS -eq 0 ]; then
   echo "Keycloak already configured"
   exit 0
fi

set -e

# intialize keycloak
ansible-galaxy collection install /app/profiles/keycloak/community-general-5.7.0.tar.gz
ansible-playbook -v /app/profiles/keycloak/keycloak-playbook.yaml

# Wait for s6 list to able able to take locks
set +e
while true; do
    #s6-rc -a list
    s6-rc-db list all
    RC=$?
    if [[ $RC == 0 ]]; then
        break
    fi
    sleep 5
done
set -e

# Restart pulp services so that settings are reloaded
SERVICES=$(s6-rc-db list all | grep -E ^pulp)
IFS=$'\n'
for SERVICE in $SERVICES; do
    echo "RESTARTING ${SERVICE}"
    s6-svc -r /var/run/service/${SERVICE}
done
echo "RESTARTING NGINX"
s6-svc -r /var/run/service/nginx
sleep 10

# this adds the social auth tables now that the INSTALLED_APPS is updated
pulpcore-manager migrate
