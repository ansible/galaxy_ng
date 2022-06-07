from django.db import transaction
#from users.models import User
from django.contrib.auth import get_user_model


from django.contrib.sessions.models import Session
from social_core.backends.github import GithubOAuth2
from social_core.exceptions import (
    AuthCanceled,
    AuthFailed,
    AuthMissingParameter,
    AuthStateForbidden,
    AuthStateMissing,
    AuthTokenError,
    AuthUnknownError
)

from urllib.parse import urlencode

from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from django.urls import reverse
from django.conf import settings
from django.shortcuts import redirect

#from api.mixins import ApiErrorsMixin, PublicApiMixin
#from users.services import user_get_or_create
#from auth.services import jwt_login, google_get_access_token, google_get_user_info
#from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import exceptions as rest_exceptions

from django.core.exceptions import ValidationError

#from utils import get_error_message
#from users.models import User

import requests


User = get_user_model()


def logged(func):
    def wrapper(*args, **kwargs):
        print(f'LOGGED: {func}')
        res = func(*args, **kwargs)
        print(f'LOGGED: {func} {res}')
        return res
    return wrapper


# https://github.com/python-social-auth
# https://github.com/python-social-auth/social-core
class GalaxyNGOAuth2(GithubOAuth2):

    '''
    @logged
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    '''

    '''
    @logged
    def validate_state(self):
        print('VALIDATING STATE')
        print(f'self.STATE_PARAMETER: {self.STATE_PARAMETER}')
        print(f'self.REDIRECT_STATE: {self.REDIRECT_STATE}')

        #return super().validate_state()

        """Validate state value. Raises exception on error, returns state
        value if valid."""
        if not self.STATE_PARAMETER and not self.REDIRECT_STATE:
            print('validate_state return None because not self.STATE_PARAMETER and not self.REDIRECT_STATE')
            return None

        for sess in Session.objects.iterator():
            print(f'SESSION: {sess.get_decoded()}')

        state = self.get_session_state()
        print(f'state == {state}')

        request_state = self.get_request_state()
        print(f'request_state == {request_state}')

        if not request_state:
            raise AuthMissingParameter(self, 'state')

        elif not state:
            raise AuthStateMissing(self, 'state')

        elif not constant_time_compare(request_state, state):
            raise AuthStateForbidden(self)

        else:
            return state
    '''

    '''
    @logged
    def _user_data(self, access_token, path=None):
        return super().user_data(access_token, path=path)
    '''

    @logged
    def get_session_state(self):
        #return super().get_session_state()
        param = self.name + '_state'
        print(f'SESSION_STATE PARAM: {param}')
        print(f'SESSION_STATE STRATEGY: {self.strategy}')
        sstate = self.strategy.session_get(param)
        return sstate

    @logged
    #@handle_http_errors
    def do_auth(self, access_token, *args, **kwargs):
        """Finish the auth process once the access_token was retrieved"""

        #if not isinstance(access_token, dict):
        #    access_token = parse_qs(access_token)
        #data = self.user_data(access_token)

        data = self.get_github_user(access_token)
        if data is not None and 'access_token' not in data:
            data['access_token'] = access_token
        kwargs.update({'response': data, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    '''
    @logged
    def complete(self, *args, **kwargs):
        #return super().complete(*args, **kwargs)
        return self.auth_complete(*args, **kwargs)
    '''

    @logged
    def get_github_access_token(self, code):
        rr = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            json={
                'code': code,
                'client_id': settings.SOCIAL_AUTH_GITHUB_KEY,
                'client_secret': settings.SOCIAL_AUTH_GITHUB_SECRET
            }
        )

        ds = rr.json()
        access_token = ds['access_token']
        return access_token

    @logged
    def get_github_user(self, access_token):
        rr = requests.post(
            'https://api.github.com/user',
            headers={
                'Accept': 'application/json',
                'Authorization': f'token {access_token}'
            },
        )
        return rr.json()

    @logged
    def auth_complete(self, *args, **kwargs):
        #return super().auth_complete(*args, **kwargs)
        self.process_error(self.data)

        request = kwargs['request']
        code = request.GET.get('code', None)
        access_token = self.get_github_access_token(code)

        #self.process_error(response)
        return self.do_auth(
            access_token,
            #response=response,
            *args,
            **kwargs
        )
