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
from galaxy_ng.app.api.v1.viewsets import LegacyUserViewSet

# path('articles/<int:year>/<int:month>/<slug:slug>/', views.article_detail)
urlpatterns = [
    path('imports', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports1'),
    path('imports/', LegacyRoleViewSet.as_view({"post": "create", "get": "get_task"}), name='legacy_role-imports2'),
    path('roles', LegacyRoleViewSet.as_view({"get": "list"}), name='legacy_role-list'),
    path('roles/', LegacyRoleViewSet.as_view({"get": "list"}), name='legacy_role-list2'),
    path('roles/<int:roleid>/content', LegacyRoleViewSet.as_view({"get": "get_content"}), name='legacy_role-content'),
    path('roles/<int:roleid>/content/', LegacyRoleViewSet.as_view({"get": "get_content"}), name='legacy_role-content2'),
    path('roles/<int:roleid>', LegacyRoleViewSet.as_view({"get": "get_role"}), name='legacy_role-detail'),
    path('roles/<int:roleid>/', LegacyRoleViewSet.as_view({"get": "get_role"}), name='legacy_role-detail2'),
    path('users', LegacyUserViewSet.as_view({"get": "list"}), name='legacy_users-userlist'),
    path('users/', LegacyUserViewSet.as_view({"get": "list"}), name='legacy_users-userlist2'),
    path('users/<int:userid>', LegacyUserViewSet.as_view({"get": "get_user"}), name='legacy_user-userdetail'),
    path('users/<int:userid>/', LegacyUserViewSet.as_view({"get": "get_user"}), name='legacy_user-userdetail2')
]
