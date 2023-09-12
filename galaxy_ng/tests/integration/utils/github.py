import os
import requests


class GithubAdminClient:

    baseurl = os.environ.get('SOCIAL_AUTH_GITHUB_BASE_URL')

    def list_users(self):
        url = self.baseurl + '/admin/users/list'
        rr = requests.get(url)
        return rr.json()

    def create_user(self, uid=None, login=None, email=None, password=None):
        url = self.baseurl + '/admin/users/add'
        payload = {'id': uid, 'login': login, 'email': email, 'password': password}
        rr = requests.post(url, json=payload)
        return rr.json()

    def delete_user(self, uid=None, login=None, email=None, password=None):
        url = self.baseurl + '/admin/users/remove'
        payload = {'id': uid, 'login': login}
        rr = requests.delete(url, json=payload)
        return rr.json()

    def modify_user(self, uid=None, login=None, email=None, password=None, change=None):
        if uid:
            url = self.baseurl + f'/admin/users/byid/{uid}'
        elif login:
            url = self.baseurl + f'/admin/users/bylogin/{login}'
        else:
            raise Exception('must provide either a uid or a login to find the the user')

        assert change, 'change kwarg must be used'
        assert isinstance(change, tuple), 'change kwarg must be a tuple'

        payload = {}
        payload[change[0]] = change[1]

        rr = requests.post(url, json=payload)
        return rr.json()
