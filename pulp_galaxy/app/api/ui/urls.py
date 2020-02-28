from django.urls import path, include
from rest_framework import routers

from . import viewsets


router = routers.SimpleRouter()
router.register('namespaces', viewsets.NamespaceViewSet, basename='namespaces')
router.register('my-namespaces', viewsets.MyNamespaceViewSet, basename='my-namespaces')
router.register('collections', viewsets.CollectionViewSet, basename='collections')
router.register('collection-versions',
                viewsets.CollectionVersionViewSet, basename='collection-versions')
router.register(
    'imports/collections',
    viewsets.CollectionImportViewSet,
    basename='collection-imports',
)
router.register('tags', viewsets.TagsViewSet, basename='tags')

app_name = "ui"
urlpatterns = [
    path('', include(router.urls)),
    # NOTE: Using path instead of SimpleRouter because SimpleRouter expects retrieve
    # to look up values with an ID
    path('me/', viewsets.CurrentUserViewSet.as_view({'get': 'retrieve'}))
]
