#!/usr/bin/env python

###############################################################################
#
#   local insights mitm proxy
#
#       Proxies requests from a client to the api server in a way that
#       simulates how the insights platform handles requests. Clients will
#       authenticate to the proxy with a username+pass or a token and then
#       the proxy will send the request to the api along with the appropriate
#       X_RH_IDENTITY header that is required for authentication.
#
###############################################################################


import base64
import json
import os
import uuid
import requests
import tempfile
from pprint import pprint
from requests_toolbelt.multipart.encoder import MultipartEncoder

import flask
from flask import Flask
from flask import jsonify
from flask import request


pprint(os.environ)


FILE_CACHE_DIR = '/tmp/flask-filecache'
SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', 'http://localhost:8080')
UPSTREAM_PROTO = os.environ.get('UPSTREAM_PROTO', 'http')
UPSTREAM_HOST = os.environ.get('UPSTREAM_HOST', 'localhost')
UPSTREAM_PORT = os.environ.get('UPSTREAM_PORT', '5001')
UPSTREAM_BASE_URL = f'{UPSTREAM_PROTO}://{UPSTREAM_HOST}:{UPSTREAM_PORT}'
print(f'UPSTREAM_BASE_URL: {UPSTREAM_BASE_URL}')


# Refresh tokens are what the clients use to request a bearer token from keycloak
REFRESH_TOKENS = {
    # jdoe
    '1234567890': '1',
    'abcdefghijklmnopqrstuvwxyz1234567892': '1',
    # iqe_normal_user
    '1234567891': '2',
    'abcdefghijklmnopqrstuvwxyz1234567891': '2',
    # org-admin
    '1234567892': '3',
    'abcdefghijklmnopqrstuvwxyz1234567893': '3',
    # notifications-admin
    '1234567893': '4',
    'abcdefghijklmnopqrstuvwxyz1234567894': '4',
}

# Bearer tokens are used for all api calls
BEARER_TOKENS = {}

# This set of users mimics what is found in the ephemeral environments.
USERS = {
    '1': {
        'account_number': 6089719,
        'user': {
            'username': 'jdoe',
            'email': 'jdoe@redhat.com',
            'first_name': 'john',
            'last_name': 'doe'
        }
    },
    '2': {
        'account_number': 6089723,
        'user': {
            'username': 'iqe_normal_user',
            'email': 'iqe_normal_user@redhat.com',
            'first_name': '',
            'last_name': ''
        }
    },
    '3': {
        'account_number': 6089720,
        'user': {
            'is_org_admin': True,
            'username': 'org-admin',
            'email': 'org-admin@redhat.com',
            'first_name': 'org',
            'last_name': 'admin'
        }
    },
    '4': {
        'account_number': 6089726,
        'user': {
            'username': 'notifications_admin',
            'email': 'notifications_admin@redhat.com',
            'first_name': 'notifications',
            'last_name': 'admin'
        }
    }
}

# The entitlements server in ephemeral provides this data for each user
ENTITLEMENTS = {
    'insights': {'is_entitled': True, 'is_trial': False}
}


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = FILE_CACHE_DIR
os.makedirs(FILE_CACHE_DIR, exist_ok=True)


def userid_to_identity(user_id):
    """
    Build the encoded header that will be passed to the api
    """
    x_rh_identity = {
        'entitlements': ENTITLEMENTS,
        'identity': USERS[user_id]
    }
    id_dumped = json.dumps(x_rh_identity)
    id_bytes = id_dumped.encode('ascii')
    id_encoded = base64.b64encode(id_bytes)
    return id_encoded


@app.route('/auth/realms/redhat-external/protocol/openid-connect/token', methods=['POST'])
def do_login():
    """
    Return a bearer token for the user
    """
    refresh_token = request.form.get('refresh_token')
    user_id = REFRESH_TOKENS[refresh_token]
    bearer_token = str(uuid.uuid4())
    BEARER_TOKENS[bearer_token] = user_id
    return jsonify({'access_token': bearer_token})


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def get_dir(path):
    """
    Handle all paths not related to keycloak/SSO
    """

    print('\n\n# NEW REQUEST ..........................................')
    print(path)
    print(request.headers)

    # FIXME - urljoins in the integration tests seem wrong?
    _path = path
    if '//' in path:
        path = path.replace('//', '/')

    auth = request.headers.get('Authorization')
    print(f'auth: {auth}')

    # Find the userid whether it's basic or token auth ...
    if 'Bearer' in auth:
        bearer_token = auth.replace('Bearer', '').strip()
        user_id = BEARER_TOKENS[bearer_token]
    elif 'Basic' in auth:
        auth = request.authorization
        un = auth['username']
        # pw = auth['password']
        for k, v in USERS.items():
            if v['user']['username'] == un:
                user_id = k
                break

    print(f'USER: {USERS[user_id]}')

    # assemble the base set of headers with the identity
    headers = {}
    # django is going to replace - with _ and prefix with HTTP_
    headers['X-RH-IDENTITY'] = userid_to_identity(user_id)

    if request.method == 'POST':

        # Post requests are special when files are involved. A recent ansible client
        # and most integration tests will POST a multi-part form that includes a base64
        # encoded blob. Ansible 2.9 has a bug in it's creation of multi-part uploads
        # that isn't compatible with werkzeug, so some hacking is necessary to get the
        # raw stream of data so it can be passed to the upstream.

        if request.files:
            # This is the easy path where the form data is not malformed ...

            print(f'POST1 to {path} {request.files}')
            uploaded_file = request.files['file']
            fn = os.path.join(FILE_CACHE_DIR, uploaded_file.filename)
            ds = uploaded_file.stream.read()
            ds = base64.b64decode(ds)
            with open(fn, 'wb') as f:
                f.write(ds)

            mp_encoder = MultipartEncoder(fields={
                'file': (os.path.basename(fn), open(fn, 'rb'))
            })
            headers['Content-Type'] = mp_encoder.content_type

            rr = requests.post(
                UPSTREAM_BASE_URL + '/' + path.lstrip('/'),
                allow_redirects=False,
                headers=headers,
                data=mp_encoder
            )

            os.remove(fn)
            return jsonify(rr.json()), rr.status_code

        elif request.mimetype == 'multipart/form-data':
            # This is the workaround path for ansible 2.9 and the integration
            # tests that intentionally malform the the data to replicate the bug.

            # The data stream as implemented in werkzeug is read-once and there is
            # no way to ever get that raw data again once the form parsers have run.
            # Unfortunately since the form data is bad, the "files" property is empty.
            # My fork of werkzeug includes a patch to save the data to a private
            # field immediately after the stream is read.
            ds = request.stream._raw_data

            # Replicate the content-type
            headers['Content-Type'] = request.headers['Content-Type']

            # Pass the stream data directly upstream
            rr = requests.post(
                UPSTREAM_BASE_URL + '/' + path.lstrip('/'),
                allow_redirects=False,
                headers=headers,
                data=ds
            )

            return jsonify(rr.json()), rr.status_code

        # This should be a normal POST request without any form data
        rr = requests.post(
            UPSTREAM_BASE_URL + '/' + path.lstrip('/'),
            allow_redirects=False,
            headers=headers,
            json=request.json
        )

        # Make a new response object with the raw text
        resp = flask.Response(rr.text)

        # Set the status code
        resp.status_code = rr.status_code

        # Set the content-type for the client
        resp.headers['Content-Type'] = rr.headers['Content-Type']

        # Make sure the client is told about redirects
        if rr.headers.get('Location'):
            resp.headers['Location'] = rr.headers['Location']

        print('v------------ RESPONSE')
        print(resp)
        print('^------------ RESPONSE')

        return resp

    ############################################################################
    #   GET / PUT / DELETE
    ############################################################################

    # FIXME: This is a workaround for duplicate slashes in the urls
    get_url = request.url.replace(SERVER_BASE_URL, UPSTREAM_BASE_URL)
    get_url = get_url.replace(_path, _path.replace('//', '/'))
    print(get_url)

    # Abstract the method so we don't have to make an algorithm
    func = getattr(requests, request.method.lower())

    if request.method == 'PUT':
        # PUT is like a POST and will usually have data to send
        headers['Content-Type'] = request.headers['Content-Type']
        rr = func(
            get_url,
            data=request.data,
            allow_redirects=False,
            headers=headers
        )
    else:
        # GET / DELETE
        rr = func(
            get_url,
            allow_redirects=False,
            headers=headers
        )

    print(rr.headers)

    # If the response is a tar file, save it and then send it back to the client.
    if rr.headers['Content-Type'] == 'application/x-tar':
        fn = os.path.basename(path)
        tdir = tempfile.mkdtemp()
        fn = os.path.join(tdir, fn)
        with open(fn, 'wb') as f:
            f.write(rr.content)
        return flask.send_file(fn)

    # Replace internal urls in the response data with the proxy's url
    rtxt = rr.text
    if rr.headers['Content-Type'] in ['application/json', 'application/text']:
        rtxt = rtxt.replace('http://localhost:8002', 'http://localhost:8080/')

    try:
        pprint(json.loads(rtxt))
    except Exception:
        print(rtxt)

    # Assemble a new response
    resp = flask.Response(rtxt)
    resp.status_code = rr.status_code
    resp.headers['Content-Type'] = rr.headers['Content-Type']
    if rr.headers.get('Location'):
        resp.headers['Location'] = rr.headers['Location']

    print('v------------ RESPONSE')
    print(resp)
    print('^------------ RESPONSE')

    return resp


if __name__ == '__main__':
    if os.environ.get('API_SECURE'):
        app.run(ssl_context='adhoc', host='0.0.0.0', port=8443, debug=True)
    else:
        app.run(host='0.0.0.0', port=8080, debug=True)
