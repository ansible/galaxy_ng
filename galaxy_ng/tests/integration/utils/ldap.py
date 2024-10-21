#!/usr/bin/env python

import atexit
import base64
import hashlib
from typing import Optional

from ldap3 import Server, Connection, ALL


class LDAPAdminClient:
    """
    A simple admin client for https://github.com/rroemhild/docker-test-openldap
    """

    def __init__(self):
        LDAP_SERVER = 'ldap://ldap:10389'
        BIND_DN = 'cn=admin,dc=planetexpress,dc=com'
        BIND_PASSWORD = 'GoodNewsEveryone'
        self.server = Server(LDAP_SERVER, get_info=ALL)

        # check the connection ...
        self.connection = Connection(self.server, BIND_DN, BIND_PASSWORD, auto_bind=True)
        if not self.connection.bind():
            raise Exception(f"Failed to authenticate: {self.connection.result}")

        atexit.register(self.connection.unbind)

    def crypt_password(self, password: str) -> str:
        sha1_hash = hashlib.sha1(password.encode('utf-8')).digest()
        return '{SHA}' + base64.b64encode(sha1_hash).decode('utf-8')

    def create_user(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        dn = f'cn={username},ou=people,dc=planetexpress,dc=com'
        crypted_password = self.crypt_password(password)
        user_ldif = {
            'cn': username,
            'sn': username,
            'uid': username,
            'mail': f'{username}@planetexpress.com',
            'objectClass': ['inetOrgPerson', 'organizationalPerson', 'person', 'top'],
            'userPassword': crypted_password,
        }
        return self.connection.add(dn, attributes=user_ldif)
