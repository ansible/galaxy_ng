import json
import re

import requests
from galaxykit import GalaxyClient


def test_github(galaxy_client):
    '''
    auth = {
        "username": "github-qe-test-user",
        "password": "iWvFM@9Jj5Eckuy",
    }
    url = "https://beta-galaxy-stage.ansible.com/api/"
    g_client = GalaxyClient(galaxy_root=url, auth=auth, github_social_auth=True)
    r = g_client.get("_ui/v1/me/")
    '''

    auth = {
        "username": "github-qe-test-user",
        "password": "iWvFM@9Jj5Eckuy",
    }
    # gc = galaxy_client("github_user", github_social_auth=True)
    gc = galaxy_client(auth, github_social_auth=True)
    r = gc.get("_ui/v1/me/")
