import datetime
import time

from django.urls import include, path
from rest_framework import routers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.tasking import dispatch
from pulpcore.app.models import Task
from pulpcore.plugin.models import ContentArtifact
from pulp_ansible.app.models import CollectionVersion
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.v1.viewsets import LegacyRoleViewSet


urlpatterns = [
    path('imports', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports1'),
    path('imports/', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports2'),
    path('roles', LegacyRoleViewSet.as_view({"get": "list"}), name='legacy_role-list'),
    path('roles/', LegacyRoleViewSet.as_view({"get": "list"}), name='legacy_role-list2')
]
