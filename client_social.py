#!/usr/bin/env python3

import requests
from pprint import pprint

baseurl = 'http://localhost:5001'
me_url = baseurl + '/api/_ui/v1/me/'
complete_url = baseurl + '/complete/github/'

# start the login sequence by getting a csrf token
rs = requests.Session()
rr1 = rs.get('http://localhost:8082/login/oauth/authorize')
csrftoken = rr1.cookies['csrftoken']

# send the credentials
rr2 = rs.post(
    'http://localhost:8082/login/oauth/authorize',
    cookies={'csrftoken': csrftoken},
    json={'username': 'gh01', 'password': 'redhat'}
)

# a background request is made to api.github.com/login/oauth/access_token
# a background request is made to api.github.com/user

sessionid = rr2.cookies['sessionid']
csrftoken = rr2.cookies['csrftoken']
print(f'SESSIONID: {sessionid}')
print(f'CSRFTOKEN: {csrftoken}')


# Check the user ...
rr3 = rs.get(
    me_url,
    headers={'X-CSRFToken': csrftoken},
    cookies={'sessionid': sessionid, 'csrftoken': csrftoken}
)
user = rr3.json()
user.pop('model_permissions', None)
pprint(user)

import epdb; epdb.st()
