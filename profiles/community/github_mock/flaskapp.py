#!/usr/bin/env python

###############################################################################
#
#   local github social auth mock
#
#       Implements just enough of github.com to supply what is needed for api
#       tests to do github social auth (no browser).
#
###############################################################################


import os
import uuid
import random
import string
import sqlite3
# import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect


app = Flask(__name__)

# for mutable users
db_name = 'user_database.db'

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
        'password': 'redhat',
        'email': 'gh01@gmail.com',
    },
    'gh02': {
        'id': 1001,
        'login': 'gh02',
        'password': 'redhat',
        'email': 'gh02@gmail.com',
    },
    'jctannerTEST': {
        'id': 1003,
        'login': 'jctannerTEST',
        'password': 'redhat',
        'email': 'jctannerTEST@gmail.com',
    },
    'geerlingguy': {
        'id': 481677,
        'login': 'geerlingguy',
        'password': 'redhat',
        'email': 'geerlingguy@nohaxx.me',
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


def create_tables():

    if os.path.exists(db_name):
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

    for uname, uinfo in USERS.items():
        sql = "INSERT OR IGNORE INTO users (id, login, email, password) VALUES(?, ?, ?, ?)"
        print(sql)
        cursor.execute(sql, (uinfo['id'], uinfo['login'], uinfo['email'], uinfo['password'],))
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_tokens (
            access_token TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS csrf_tokens (
            csrf_token TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    conn.close()


def get_user_by_id(userid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT id,login,email,password FROM users WHERE id = ?', (userid,))
    row = cursor.fetchone()
    userid = row[0]
    login = row[1]
    email = row[2]
    password = row[3]
    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def get_user_by_login(login):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    print(f'FINDING USER BY LOGIN:{login}')
    cursor.execute('SELECT id,login,email,password FROM users WHERE login = ?', (login,))
    row = cursor.fetchone()
    if row is None:
        return None
    userid = row[0]
    login = row[1]
    email = row[2]
    password = row[3]
    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def get_session_by_id(sid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT id,uid FROM sessions WHERE id = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'session': rsid, 'uid': userid}


def set_session(sid, uid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into sessions (id, uid) VALUES (?, ?)',
        (sid, uid)
    )
    conn.commit()
    conn.close()


def get_access_token_by_id(sid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT access_token,uid FROM access_tokens WHERE access_token = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'access_token': rsid, 'uid': userid}


def set_access_token(token, uid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into access_tokens (access_token, uid) VALUES (?, ?)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def delete_access_token(token):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM access_tokens WHERE access_token=?',
        (token,)
    )
    conn.commit()
    conn.close()


def get_csrf_token_by_id(sid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT csrf_token,uid FROM access_tokens WHERE csrf_token = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'csrf_token': rsid, 'uid': userid}


def set_csrf_token(token, uid):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into csrf_tokens (id, uid) VALUES (?, ?)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def get_new_uid():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM users')
    highest_id = cursor.fetchone()[0]
    conn.close()
    return highest_id + 1


def get_new_login():
    return ''.join([random.choice(string.ascii_lowercase) for x in range(0, 5)])


def get_new_password():
    return ''.join([random.choice(string.ascii_lowercase) for x in range(0, 12)])


# ----------------------------------------------------


@app.route('/login/oauth/authorize', methods=['GET', 'POST'])
def do_authorization():
    """
    The client is directed here first from the galaxy UI to allow oauth
    """

    # Verify the user is authenticated?
    _gh_sess = request.cookies['_gh_sess']
    # assert _gh_sess in SESSION_IDS
    # username = SESSION_IDS[_gh_sess]
    this_session = get_session_by_id(_gh_sess)
    assert this_session
    username = get_user_by_id(this_session['uid'])
    assert username

    # Tell the backend to complete the login for the user ...
    # url = f'{API_SERVER}/complete/github/'
    url = f'{CLIENT_API_SERVER}/complete/github/'
    token = str(uuid.uuid4())
    # ACCESS_TOKENS[token] = username
    set_access_token(token, this_session['uid'])
    url += f'?code={token}'

    # FIXME
    # print(f'REDIRECT_URL: {url}')
    resp = redirect(url, code=302)
    return resp


@app.route('/login/oauth/access_token', methods=['GET', 'POST'])
def do_access_token():
    ds = request.json
    access_code = ds['code']
    # client_id = ds['client_id']
    # client_secret = ds['client_secret']

    # Match the acces_code to the username and invalidate it
    # username = ACCESS_TOKENS[access_code]
    _at = get_access_token_by_id(access_code)
    udata = get_user_by_id(_at['uid'])
    # ACCESS_TOKENS.pop(access_code, None)
    delete_access_token(access_code)

    # Make a new token
    token = str(uuid.uuid4())
    # ACCESS_TOKENS[token] = username
    set_access_token(token, udata['id'])

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
    print(f'DO_SESSION username:{username} password:{password}')
    udata = get_user_by_login(username)

    assert udata is not None, f'{username}:{password}'
    assert udata['password'] == password

    sessionid = str(uuid.uuid4())
    set_session(sessionid, udata['id'])
    # SESSION_IDS[sessionid] = username

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
    # username = ACCESS_TOKENS[token]
    token_data = get_access_token_by_id(token)
    _udata = get_user_by_id(token_data['uid'])
    username = _udata['login']
    print(username)
    # ACCESS_TOKENS.pop(token, None)
    delete_access_token(token)
    # udata = copy.deepcopy(USERS[username])
    udata = get_user_by_login(username)
    udata.pop('password', None)
    print(udata)
    return jsonify(udata)


# --------------------------------------------------------------


@app.route('/admin/users/list', methods=['GET'])
def admin_user_list():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    sql = "SELECT id, login, email, password FROM users"
    cursor.execute(sql)
    rows = cursor.fetchall()

    users = []
    for row in rows:
        userid = row[0]
        login = row[1]
        email = row[2]
        password = row[3]
        u = {'id': userid, 'login': login, 'email': email, 'password': password}
        users.append(u)

    conn.close()

    return jsonify(users)


@app.route('/admin/users/add', methods=['POST'])
def admin_add_user():
    ds = request.json

    userid = ds.get('id', get_new_uid())
    if userid is None:
        userid = get_new_uid()
    else:
        userid = int(userid)
    login = ds.get('login', get_new_login())
    if login is None:
        login = get_new_login()
    password = ds.get('password', get_new_password())
    if password is None:
        password = get_new_password()
    email = ds.get('email', login + '@github.com')
    #if email is None or not email:
    #    email = login + '@github.com'

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(f'CREATING USER {login} with {password}')
    sql = "INSERT OR IGNORE INTO users (id, login, email, password) VALUES(?, ?, ?, ?)"
    print(sql)
    cursor.execute(sql, (userid, login, email, password,))
    conn.commit()

    conn.close()
    return jsonify({'id': userid, 'login': login, 'email': email, 'password': password})


@app.route('/admin/users/remove', methods=['DELETE'])
def admin_remove_user():
    ds = request.json

    userid = ds.get('id', get_new_uid())
    if userid is None:
        userid = get_new_uid()
    login = ds.get('login', get_new_login())
    if login is None:
        login = get_new_login()

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    if userid:
        sql = 'DELETE FROM users WHERE id=?'
        cursor.execute(sql, (userid,))
        conn.commit()
    if login:
        sql = 'DELETE FROM users WHERE login=?'
        cursor.execute(sql, (login,))
        conn.commit()

    conn.close()
    return jsonify({'status': 'complete'})


@app.route('/admin/users/byid/<int:userid>', methods=['POST'])
@app.route('/admin/users/bylogin/<string:login>', methods=['POST'])
def admin_modify_user(userid=None, login=None):

    print(request.data)

    ds = request.json
    new_userid = ds.get('id')
    new_login = ds.get('login')
    new_password = ds.get('password')

    udata = None
    if userid is not None:
        udata = get_user_by_id(userid)
    elif login is not None:
        udata = get_user_by_login(login)

    print(udata)

    # must delete to change the uid
    delete = False
    if new_userid is not None and new_userid != udata['id']:
        delete = True

    if new_login is None:
        new_login = udata['id']
    if new_login is None:
        new_login = udata['login']
    if new_password is None:
        new_password = udata['password']

    if delete:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user WHERE id=?', (udata['id'],))
        conn.commit()
        cursor.execute(
            'INSERT INTO users (id, login, password) VALUES (?,?,?)',
            (new_userid, new_login, new_password,)
        )
        conn.commit()
        conn.close()

    else:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET login=?, password=? WHERE id=?',
            (new_login, new_password, udata['id'],)
        )
        conn.commit()
        conn.close()

    udata = get_user_by_login(new_login)
    return jsonify(udata)


if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=8082, debug=True)
