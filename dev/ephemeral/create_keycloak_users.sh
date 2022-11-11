#!/bin/bash

echo "configure keycloak users"
KEYCLOAK_USER=$(oc get secret env-${NAMESPACE}-keycloak -o jsonpath='{.data.username}' | base64 -d)
KEYCLOAK_PASS=$(oc get secret env-${NAMESPACE}-keycloak -o jsonpath='{.data.password}' | base64 -d)
KEYCLOAK_URL=$(oc get route -l app=env-${NAMESPACE} -o jsonpath='https://{.items[0].spec.host}')/auth
KEYCLOAK_REALM=redhat-external

TKN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "username=${KEYCLOAK_USER}" \
 -d "password=${KEYCLOAK_PASS}" \
 -d 'grant_type=password' \
 -d 'client_id=admin-cli' | jq -r '.access_token')

# set jdoe credentials/attributes
KEYCLOAK_USER_ID=$(curl -s -X GET "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
-H "Accept: application/json" \
-H "Authorization: Bearer ${TKN}" | jq -r '.[] | select(.username=="jdoe") | .id' )
curl -s -X PUT "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${KEYCLOAK_USER_ID}/reset-password" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${TKN}" \
-d '{"temporary":false,"type":"password","value":"redhat"}'
curl -s -X PUT "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${KEYCLOAK_USER_ID}" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${TKN}" \
-d '{
    "attributes": {
        "first_name": "John",
        "last_name": "Doe",
        "account_id": "6089719",
        "account_number": "6089719",
        "org_id": "3340852",
        "is_active": "true",
        "is_internal": "false",
        "is_org_admin": "false",
        "entitlements": [
            "{\"insights\": {\"is_entitled\": true, \"is_trial\": false}}"
        ],
        "newEntitlements": [
            "\"ansible\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"cost_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"insights\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"advisor\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"migrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"openshift\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"settings\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"smart_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"subscriptions\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"user_preferences\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"notifications\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"integrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"automation_analytics\": {\"is_entitled\": true, \"is_trial\": false}"
        ]
    }}'

# create additional users
# iqe_normal_user
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${TKN}" \
-d '{
    "enabled": true,
    "username": "iqe_normal_user",
    "firstName": "RBAC",
    "lastName": "Normal",
    "email": "iqe_normal_user@redhat.com",
    "attributes": {
        "first_name": "RBAC",
        "last_name": "Normal",
        "account_id": "6089723",
        "account_number": "6089723",
        "org_id": "None",
        "is_active": "true",
        "is_internal": "false",
        "is_org_admin": "false",
        "entitlements": [
            "{\"insights\": {\"is_entitled\": true, \"is_trial\": false}}"
        ],
        "newEntitlements": [
            "\"ansible\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"cost_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"insights\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"advisor\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"migrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"openshift\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"settings\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"smart_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"subscriptions\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"user_preferences\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"notifications\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"integrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"automation_analytics\": {\"is_entitled\": true, \"is_trial\": false}"
        ]
    },
    "credentials": [{
        "temporary": false,
        "type": "password",
        "value": "redhat"
    }]
    }'

# org-admin
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${TKN}" \
-d '{
    "enabled": true,
    "username": "org-admin",
    "firstName": "Org",
    "lastName": "Admin",
    "email": "org-admin@redhat.com",
    "attributes": {
        "first_name": "Org",
        "last_name": "Admin",
        "account_id": "6089720",
        "account_number": "6089720",
        "org_id": "12346",
        "is_active": "true",
        "is_internal": "true",
        "is_org_admin": "true",
        "entitlements": [
            "{\"insights\": {\"is_entitled\": true, \"is_trial\": false}}"
        ],
        "newEntitlements": [
            "\"ansible\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"cost_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"insights\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"advisor\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"migrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"openshift\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"settings\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"smart_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"subscriptions\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"user_preferences\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"notifications\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"integrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"automation_analytics\": {\"is_entitled\": true, \"is_trial\": false}"
        ]
    },
    "credentials": [{
        "temporary": false,
        "type": "password",
        "value": "redhat"
    }]
    }'

# notifications_admin
curl -s -X POST "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${TKN}" \
-d '{
    "enabled": true,
    "username": "notifications_admin",
    "firstName": "notifications",
    "lastName": "admin",
    "email": "notifications_admin@redhat.com",
    "attributes": {
        "first_name": "notifications",
        "last_name": "admin",
        "account_id": "6089726",
        "account_number": "6089726",
        "org_id": "12345",
        "is_active": "true",
        "is_internal": "false",
        "is_org_admin": "false",
        "entitlements": [
            "{\"insights\": {\"is_entitled\": true, \"is_trial\": false}}"
        ],
        "newEntitlements": [
            "\"ansible\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"cost_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"insights\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"advisor\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"migrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"openshift\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"settings\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"smart_management\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"subscriptions\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"user_preferences\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"notifications\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"integrations\": {\"is_entitled\": true, \"is_trial\": false}",
            "\"automation_analytics\": {\"is_entitled\": true, \"is_trial\": false}"
        ]
    },
    "credentials": [{
        "temporary": false,
        "type": "password",
        "value": "redhat"
    }]
    }'
