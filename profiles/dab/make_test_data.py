#!/usr/bin/env python

import os
import requests
import warnings


warnings.filterwarnings("ignore")


HUB_API_ROOT = "https://localhost/api/galaxy/"
GW_ROOT_URL = "https://localhost"

# 26 export AAP_GATEWAY_ADMIN_USERNAME=admin
# 27 export AAP_GATEWAY_ADMIN_PASSWORD=admin
ADMIN_AUTH = (
    os.environ.get('AAP_GATEWAY_ADMIN_USERNAME', 'admin'),
    os.environ.get('AAP_GATEWAY_ADMIN_PASSWORD', 'redhat1234')
)

NAMESPACES = ("autohubtest2", "autohubtest3", "signing")
USERS = ("notifications_admin", "iqe_normal_user", "jdoe", "org-admin", "iqe_admin", "ee_admin")

# FIXME - this seems to be dependant on not having a gateway
GROUP = "ns_group_for_tests"
NS_OWNER_DEF = "galaxy.collection_namespace_owner"


# MAP OUT THE ROLES ..
rr = requests.get(
    GW_ROOT_URL + '/api/galaxy/_ui/v2/role_definitions/',
    verify=False,
    auth=ADMIN_AUTH
)
ROLEDEFS = {x['name']: x for x in rr.json()['results']}

# MAP OUT THE PULP ROLES ...
rr = requests.get(
    GW_ROOT_URL + '/api/galaxy/pulp/api/v3/roles/',
    verify=False,
    auth=ADMIN_AUTH
)
PULP_ROLEDEFS = {x['name']: x for x in rr.json()['results']}


# MAP OUT THE REPOS ...
rr = requests.get(
    GW_ROOT_URL + '/api/galaxy/pulp/api/v3/repositories/ansible/ansible/',
    verify=False,
    auth=ADMIN_AUTH
)
REPOS = {x['name']: x for x in rr.json()['results']}


# MAKE AND MAP THE USERS ...
umap = {}
for USERNAME in USERS:

    payload = {'username': USERNAME, 'password': 'redhat'}
    if USERNAME in ["notifications_admin", "iqe_admin", "ee_admin"]:
        payload['is_superuser'] = True

    rr = requests.get(
        GW_ROOT_URL + f'/api/gateway/v1/users/?username={USERNAME}',
        verify=False,
        auth=ADMIN_AUTH
    )
    if rr.json()['count'] > 0:
        udata = rr.json()['results'][0]
    else:
        rr = requests.post(
            GW_ROOT_URL + '/api/gateway/v1/users/',
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )
        udata = rr.json()

    umap[USERNAME] = udata

    # get the galaxy data ...
    rr = requests.get(
        GW_ROOT_URL + f'/api/galaxy/_ui/v2/users/?username={USERNAME}',
        verify=False,
        auth=ADMIN_AUTH
    )
    umap[USERNAME]['galaxy'] = rr.json()['results'][0]

    if USERNAME == "jdoe":
        userid = umap[USERNAME]["galaxy"]["id"]
        # PERMISSION = "ansible.modify_ansible_repo_content"
        # ROLE = "ansible.ansiblerepository_viewer"
        payload = {
            "role": "ansible.ansiblerepository_viewer",
            "content_object": None,
        }
        prr = requests.post(
            GW_ROOT_URL + f"/api/galaxy/pulp/api/v3/users/{userid}/roles/",
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )

        payload = {
            "role": "ansible.ansiblerepository_owner",
            "content_object": None,
        }
        prr2 = requests.post(
            GW_ROOT_URL + f"/api/galaxy/pulp/api/v3/users/{userid}/roles/",
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )

        payload = {
            "role": "galaxy.collection_admin",
            "content_object": None,
        }
        prr3 = requests.post(
            GW_ROOT_URL + f"/api/galaxy/pulp/api/v3/users/{userid}/roles/",
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )

        # import epdb; epdb.st()


# MAKE THE NAMESPACES ...
for NAMESPACE in NAMESPACES:
    rr = requests.get(
        GW_ROOT_URL + f'/api/galaxy/_ui/v1/namespaces/{NAMESPACE}/',
        verify=False,
        auth=ADMIN_AUTH
    )
    if rr.status_code == 404:
        prr = requests.post(
            GW_ROOT_URL + '/api/galaxy/_ui/v1/namespaces/',
            verify=False,
            auth=ADMIN_AUTH,
            json={"name": NAMESPACE, "groups": [], "users": []}
        )
        nsdata = prr.json()
    else:
        nsdata = rr.json()

    # continue

    '''
    # add owner role for each user ..
    for USERNAME, udata in umap.items():

        # normal users shouldn't have any roles ...
        if USERNAME in ['jdoe', 'iqe_normal_user']:
            continue

        payload = {
            # "role_definition": ROLEDEFS["galaxy.collection_namespace_owner"]["id"],
            "role_definition": ROLEDEFS["galaxy.content_admin"]["id"],
            # "object_id": nsdata['id'],
            "user": udata["galaxy"]["id"]
        }
        prr = requests.post(
            GW_ROOT_URL + '/api/galaxy/_ui/v2/role_user_assignments/',
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )

        # galaxy.execution_environment_admin
        payload['role_definition'] = ROLEDEFS["galaxy.execution_environment_admin"]["id"]
        prr = requests.post(
            GW_ROOT_URL + '/api/galaxy/_ui/v2/role_user_assignments/',
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )
    '''

    for USERNAME, udata in umap.items():

        if USERNAME not in ['jdoe']:
            continue

        # give a pulp level role+perms on this namespace ...
        userid = udata["galaxy"]["id"]
        role_id = PULP_ROLEDEFS["galaxy.collection_namespace_owner"]["pulp_href"].split("/")[-2]
        payload = {
            "role": "galaxy.collection_namespace_owner",
            "content_object": nsdata["pulp_href"],
        }
        prr = requests.post(
            GW_ROOT_URL + f"/api/galaxy/pulp/api/v3/users/{userid}/roles/",
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )


'''
# GIVE EACH USER APPROVER TO EACH REPO ...
for reponame in ['validated', 'rh-certified', 'community', 'published', 'rejected', 'staging']:
    repodata = REPOS[reponame]
    pk = repodata['pulp_href'].split('/')[-2]
    for USERNAME, udata in umap.items():
        payload = {
            "role_definition": ROLEDEFS["galaxy.normal_user_collection_approver"]["id"],
            "object_id": pk,
            "user": udata["galaxy"]["id"]
        }
        prr = requests.post(
            GW_ROOT_URL + '/api/galaxy/_ui/v2/role_user_assignments/',
            verify=False,
            auth=ADMIN_AUTH,
            json=payload
        )
        #import epdb; epdb.st()
'''
