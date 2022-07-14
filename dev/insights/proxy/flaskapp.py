#!/usr/bin/env python


import base64
import json
import io
import os
import uuid
import requests
import tempfile
import email.mime.application
from pprint import pprint
from unittest.mock import patch
from requests_toolbelt.multipart.encoder import MultipartEncoder

from werkzeug.wsgi import LimitedStream
from werkzeug.datastructures import ImmutableOrderedMultiDict
from unittest.mock import patch

import flask
from flask import Flask
from flask import Request
from flask import jsonify
from flask import request
from flask import redirect


pprint(os.environ)


FILE_CACHE_DIR = '/tmp/flask-filecache'
SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', 'http://localhost:8080')
UPSTREAM_PROTO = os.environ.get('UPSTREAM_PROTO', 'http')
UPSTREAM_HOST = os.environ.get('UPSTREAM_HOST', 'localhost')
UPSTREAM_PORT = os.environ.get('UPSTREAM_PORT', '5001')
UPSTREAM_BASE_URL = f'{UPSTREAM_PROTO}://{UPSTREAM_HOST}:{UPSTREAM_PORT}'
print(f'UPSTREAM_BASE_URL: {UPSTREAM_BASE_URL}')

BEARER_TOKENS = {}

REFRESH_TOKENS = {
    '1234567890': '1',
    '1234567891': '2',
    '1234567892': '3',
    '1234567893': '4',
}

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

ENTITLEMENTS = {
    'insights': {'is_entitled': True, 'is_trial': False}
}


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = FILE_CACHE_DIR


if not os.path.exists(FILE_CACHE_DIR):
    os.makedirs(FILE_CACHE_DIR)


class LoggingMiddleware(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, env, resp):
        errorlog = env['wsgi.errors']
        pprint(('REQUEST', env), stream=errorlog)

        def log_response(status, headers, *args):
            pprint(('RESPONSE', status, headers), stream=errorlog)
            return resp(status, headers, *args)

        return self._app(env, log_response)


"""
class StreamFixerMiddleware(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, env, resp):


        if env['REQUEST_METHOD'] == 'POST':

            #env['werkzeug.request'].test_bit = True

            '''
            req = env['werkzeug.request']
            print('READ STREAM')
            sdata = req.stream.read()
            print('SET STREAM RAW')
            env['werkzeug.request'].stream_raw = sdata
            print('REBIND STREAM')

            _stream = io.BytesIO(sdata)
            env['werkzeug.request'].stream = LimitedStream(_stream, len(sdata))
            '''

            #import epdb; epdb.st()
            pass


        print('CALL DONE')

        print(f'resp id: {id(resp)}')
        print(f"w.request id: {id(env['werkzeug.request'])}")

        return self._app(env, resp)
"""


def userid_to_identity(user_id):
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
    refresh_token = request.form.get('refresh_token')
    user_id = REFRESH_TOKENS[refresh_token]
    bearer_token = str(uuid.uuid4())
    BEARER_TOKENS[bearer_token] = user_id
    return jsonify({'access_token': bearer_token})


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def get_dir(path):
    print('\n\n# NEW REQUEST ..........................................')
    print(path)
    print(request.headers)

    # FIXME - urljoins in the integration tests seem wrong?
    _path = path
    if '//' in path:
        path = path.replace('//', '/')

    auth = request.headers.get('Authorization')
    print(f'auth: {auth}')

    if 'Bearer' in auth:
        bearer_token = auth.replace('Bearer', '').strip()
        print(bearer_token)
        user_id = BEARER_TOKENS[bearer_token]

    elif 'Basic' in auth:
        auth = request.authorization
        un = auth['username']
        pw = auth['password']
        for k,v in USERS.items():
            if v['user']['username'] == un:
                user_id = k
                break

    print(f'USER: {USERS[user_id]}')

    headers = {}
    headers['X_RH_IDENTITY'] = userid_to_identity(user_id)

    if request.method == 'POST':

        print(f'POST to {path} {request.files}')
        #import epdb; epdb.st()

        if request.files:
            # This is how the CLI uploads a collection
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

            # if rr.status_code == 400:
            #    import epdb; epdb.st()

            return jsonify(rr.json()), rr.status_code

        elif request.mimetype == 'multipart/form-data':
            print(f'POST2 to {path} {request.files}')

            # This is how upload_artifact in the tests works ...

            #fs = request._get_file_stream(request.content_length, request.content_type)
            #ds = fs.read()
            print('STUFF')
            #ds = request.stream.read()

            ds = request.stream._raw_data
            #ds = request.stream_raw
            #import epdb; epdb.st()

            body_parts = ds.partition(b'Content-Disposition: form-data; name="sha256"\r\n')
            new_stream = io.BytesIO()
            new_stream.write(body_parts[0])
            new_stream.write(body_parts[1])
            if not body_parts[2].startswith(b'\r\n'):
                new_stream.write(b'\r\n')
            new_stream.write(body_parts[2])
            new_stream.seek(0)

            headers['Content-Type'] = request.headers['Content-Type']
            #import epdb; epdb.st()

            '''
            if len(ds) != request.content_length:
                print('BAD content length')
                import epdb; epdb.st()
                return jsonify({'errors': [{
                    'code': 'invalid',
                    'detail': 'invalid file upload',
                    'status': '400',
                    'source': {'parameter': 'file'}
                }]}), 400
            '''

            print('What now?')
            rr = requests.post(
                UPSTREAM_BASE_URL + '/' + path.lstrip('/'),
                allow_redirects=False,
                headers=headers,
                data=ds
            )
            #import epdb; epdb.st()

            return jsonify(rr.json()), rr.status_code


        print(f'POST3 to {path}')
        rr = requests.post(
            UPSTREAM_BASE_URL + '/' + path.lstrip('/'),
            allow_redirects=False,
            headers=headers,
            json=request.json
        )

        resp = flask.Response(rr.text)
        resp.status_code = rr.status_code
        resp.headers['Content-Type'] = rr.headers['Content-Type']
        if rr.headers.get('Location'):
            resp.headers['Location'] = rr.headers['Location']

        print('v------------ RESPONSE')
        print(resp)
        print('^------------ RESPONSE')

        return resp




    # SERVER_BASE_URL = 'http://localhost:8080'
    # UPSTREAM_BASE_URL = 'http://localhost:5001'
    get_url = request.url.replace(SERVER_BASE_URL, UPSTREAM_BASE_URL)
    get_url = get_url.replace(_path, _path.replace('//', '/'))
    print(get_url)

    func = getattr(requests, request.method.lower())

    if request.method == 'PUT':
        headers['Content-Type'] = request.headers['Content-Type']
        rr = func(
            get_url,
            data=request.data,
            allow_redirects=False,
            headers=headers
        )
    else:
        rr = func(
            get_url,
            allow_redirects=False,
            headers=headers
        )

    print(rr.headers)

    rtxt = rr.text
    if rr.headers['Content-Type'] in ['application/json', 'application/text']:
        rtxt = rtxt.replace('http://localhost:8002', 'http://localhost:8080/')

    if rr.headers['Content-Type'] == 'application/x-tar':
        fn = os.path.basename(path)
        tdir = tempfile.mkdtemp()
        fn = os.path.join(tdir, fn)
        with open(fn, 'wb') as f:
            f.write(rr.content)
        return flask.send_file(fn)

    rtxt = rr.text
    if rr.headers['Content-Type'] in ['application/json', 'application/text']:
        rtxt = rtxt.replace('http://localhost:8002', 'http://localhost:8080/')

    print(rtxt)
    try:
        pprint(json.loads(rtxt))
    except:
        pass

    resp = flask.Response(rtxt)
    resp.status_code = rr.status_code
    resp.headers['Content-Type'] = rr.headers['Content-Type']
    if rr.headers.get('Location'):
        resp.headers['Location'] = rr.headers['Location']

    print('v------------ RESPONSE')
    print(resp)
    print('^------------ RESPONSE')

    #if rr.status_code == 405:
    #    import epdb; epdb.st()

    return resp




if __name__ == '__main__':
    #app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    #app.wsgi_app = StreamFixerMiddleware(app.wsgi_app)
    if os.environ.get('API_SECURE'):
        app.run(ssl_context='adhoc', host='0.0.0.0', port=8443, debug=True)
    else:
        app.run(host='0.0.0.0', port=8080, debug=True)
