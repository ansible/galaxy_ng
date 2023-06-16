#!/usr/bin/env python

###############################################################################
#
#   local github social auth mock
#
#       Implements just enough of github.com to supply what is needed for api
#       tests to do github social auth (no browser).
#
###############################################################################


import copy
import os
import uuid
# import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect


app = Flask(__name__)


# When run inside a container, we need to know how to talk to the galaxy api
UPSTREAM_PROTO = os.environ.get('UPSTREAM_PROTO')
UPSTREAM_HOST = os.environ.get('UPSTREAM_HOST')
UPSTREAM_PORT = os.environ.get('UPSTREAM_PORT')
if all([UPSTREAM_PROTO, UPSTREAM_HOST, UPSTREAM_PORT]):
    UPSTREAM = UPSTREAM_PROTO + '://' + UPSTREAM_HOST + ':' + UPSTREAM_PORT
else:
    # When this flaskapp is run on the host,
    # the api server will be available on port 5001
    UPSTREAM = 'http://localhost:5001'

# Make it simple to set the API server url or default to upstream
API_SERVER = os.environ.get('GALAXY_API_SERVER', UPSTREAM)

# How does the client talk to the API?
CLIENT_API_SERVER = os.environ.get('CLIENT_GALAXY_API_SERVER', 'http://localhost:5001')

print(f'API_SERVER: {API_SERVER}')

# This is the serialized user data that github would provide
USERS = {
    'gh01': {
        'id': 1000,
        'login': 'gh01',
        'password': 'redhat'
    },
    'gh02': {
        'id': 1001,
        'login': 'gh02',
        'password': 'redhat'
    },
    'jctannerTEST': {
        'id': 1003,
        'login': 'jctannerTEST',
        'password': 'redhat'
    },
    'geerlingguy': {
        'id': 1004,
        'login': 'geerlingguy',
        'password': 'redhat'
    }
}

# These are used for initial form GET+POST
CSRF_TOKENS = {
}

# These will be one time tokens that are used to get the user info
ACCESS_TOKENS = {
}

# These are given at login time
SESSION_IDS = {
}


# Github authorization redirect sequence ...
# /login/oauth/authorize -> /login -> /session -> /login/oauth/authorize

# Backend response sequence ...
# /complete/github/?code=9257c509396232aa4f67 -> /accounts/profile


@app.route('/login/oauth/authorize', methods=['GET', 'POST'])
def do_authorization():
    """
    The client is directed here first from the galaxy UI to allow oauth
    """

    """
    # The client should do a GET first to grab the
    # initial CSRFToken.
    if request.method == 'GET':
        resp = jsonify({})
        csrftoken = str(uuid.uuid4())
        CSRF_TOKENS[csrftoken] = None
        resp.set_cookie('csrftoken', csrftoken)
        return resp

    # Assert a valid CSRFtoken is being used ?
    inc_csrftoken = request.cookies.get('csrftoken')
    if inc_csrftoken:
        assert inc_csrftoken in CSRF_TOKENS
        CSRF_TOKENS.pop(inc_csrftoken, None)

    # Get the creds
    ds = request.json
    username = ds['username']
    password = ds['password']
    assert username in USERS
    assert USERS[username]['password'] == password
    """

    # Verify the user is authenticated?
    _gh_sess = request.cookies['_gh_sess']
    assert _gh_sess in SESSION_IDS
    username = SESSION_IDS[_gh_sess]

    # Tell the backend to complete the login for the user ...
    # url = f'{API_SERVER}/complete/github/'
    url = f'{CLIENT_API_SERVER}/complete/github/'
    token = str(uuid.uuid4())
    ACCESS_TOKENS[token] = username
    url += f'?code={token}'

    # FIXME
    # print(f'REDIRECT_URL: {url}')
    resp = redirect(url, code=302)
    return resp

    '''
    print(f'GET {url}')
    rr = requests.get(url, allow_redirects=False)

    # The response provides 2 cookies that the client will need
    # to use for all future authentication to the galaxy api ...
    """
    (Epdb) rr.cookies.keys()
    ['csrftoken', 'sessionid']
    (Epdb) rr.cookies['csrftoken']
    'tafP2W3kdp4xLu4mOuXZQSVNXSYtF5Xq2k8Y3mb6sn2K2jz1PdmpxliDxvRbd7ze'
    (Epdb) rr.cookies['sessionid']
    'alc04ie74vhx9l9k385htwusq1g25jhg'
    """
    csrftoken = rr.cookies.get('csrftoken')
    sessionid = rr.cookies.get('sessionid')

    resp = jsonify({})
    if csrftoken:
        resp.set_cookie('csrftoken', csrftoken, samesite='Lax')
    if sessionid:
        resp.set_cookie('sessionid', sessionid, samesite='Lax')

    return resp
    '''


@app.route('/login/oauth/access_token', methods=['GET', 'POST'])
def do_access_token():
    ds = request.json
    access_code = ds['code']
    # client_id = ds['client_id']
    # client_secret = ds['client_secret']

    # Match the acces_code to the username and invalidate it
    username = ACCESS_TOKENS[access_code]
    ACCESS_TOKENS.pop(access_code, None)

    # Make a new token
    token = str(uuid.uuid4())
    ACCESS_TOKENS[token] = username

    return jsonify({'access_token': token})


# The github login page will post form data here ...
@app.route('/session', methods=['POST'])
def do_session():

    """
    if request.method == 'GET':
        resp = jsonify({})
        csrftoken = str(uuid.uuid4())
        CSRF_TOKENS[csrftoken] = None
        resp.set_cookie('csrftoken', csrftoken)
        return resp
    """

    # form data ...
    #   username
    #   password

    username = request.form.get('username')
    password = request.form.get('password')

    assert username in USERS
    assert USERS[username]['password'] == password

    sessionid = str(uuid.uuid4())
    SESSION_IDS[sessionid] = username

    resp = jsonify({})
    resp.set_cookie('_gh_sess', sessionid)
    resp.set_cookie('_user_session', sessionid)
    resp.set_cookie('dotcom_user', username)
    resp.set_cookie('logged_in', 'yes')

    return resp


@app.route('/user', methods=['GET', 'POST'])
def github_user():
    auth = request.headers['Authorization']
    print(auth)
    token = auth.split()[-1].strip()
    username = ACCESS_TOKENS[token]
    print(username)
    ACCESS_TOKENS.pop(token, None)
    udata = copy.deepcopy(USERS[username])
    udata.pop('password', None)
    print(udata)
    return jsonify(udata)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)
