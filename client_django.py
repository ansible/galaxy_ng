#!/usr/bin/env python3

import requests
from pprint import pprint

baseurl = 'http://localhost:8002'
login_url = baseurl + '/ui/login/'
login_api_url = baseurl + '/api/_ui/v1/auth/login/'
me_url = baseurl + '/api/_ui/v1/me/'

# GET the form once to have the initial csrftoken
rs = requests.Session()
rr1 = rs.get(login_api_url)
csrftoken = rr1.cookies['csrftoken']
print(f'CSRFTOKEN: {csrftoken}')

# POST credentials to the form to get the new csrftoken and sessionid
rr2 = rs.post(
    login_api_url,
    json={'username': 'admin', 'password': 'admin'},
    headers={'X-CSRFToken': csrftoken},
    cookies={'csrftoken': csrftoken}
)
csrftoken = rr2.cookies['csrftoken']
sessionid = rr2.cookies['sessionid']

# Use the csrftoken and sessionid in all future requests
rr3 = rs.get(
    me_url,
    headers={'X-CSRFToken': csrftoken},
    cookies={'csrftoken': csrftoken, 'sessionid': sessionid}
)

import epdb; epdb.st()
