import json
from django.http import HttpResponse
from django.conf import settings

def server_info(*args, **kwargs):
    ds = {
        'settings.ANSIBLE_API_HOSTNAME': settings.ANSIBLE_API_HOSTNAME,
        'settings.GALAXY_API_PATH_PREFIX': settings.GALAXY_API_PATH_PREFIX,
        'settings.X_PULP_CONTENT_HOST': settings.X_PULP_CONTENT_HOST,
        'settings.X_PULP_CONTENT_PORT': settings.X_PULP_CONTENT_PORT,
        'settings.CONTENT_PATH_PREFIX': settings.CONTENT_PATH_PREFIX
    }
    return HttpResponse(json.dumps(ds))
