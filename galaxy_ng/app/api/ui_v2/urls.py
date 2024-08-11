from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet
from .views import GroupViewSet
from .views import OrganizationViewSet
from .views import TeamViewSet

from ansible_base.rbac.urls import (
    api_version_urls as dab_rbac_urls,
)


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'teams', TeamViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns.extend(dab_rbac_urls)
