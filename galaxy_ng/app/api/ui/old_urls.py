from django.urls import path, include
from rest_framework import routers

from . import views
from . import viewsets

# TODO: remove this file once the UI has been updated to use the new versioned URLs

router = routers.SimpleRouter()
# TODO: Replace with a RedirectView
router.register('namespaces', viewsets.NamespaceViewSet, basename='namespaces')
router.register('my-namespaces', viewsets.MyNamespaceViewSet, basename='my-namespaces')
router.register('users', viewsets.UserViewSet, basename='users')
router.register('collection-versions',
                viewsets.CollectionVersionViewSet, basename='collection-versions')
router.register(
    'imports/collections',
    viewsets.CollectionImportViewSet,
    basename='collection-imports',
)
router.register('tags', viewsets.TagsViewSet, basename='tags')
router.register('synclists', viewsets.SyncListViewSet, basename='synclists')

auth_views = [
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
]

app_name = "old_ui"
urlpatterns = [
    path('', include(router.urls)),

    path('auth/', include(auth_views)),

    path(
        'collections/',
        viewsets.CollectionViewSetDeprecated.as_view({'get': 'list'}),
        name='collections-list'
    ),
    path(
        'collections/<str:namespace>/<str:name>/',
        viewsets.CollectionViewSetDeprecated.as_view({'get': 'retrieve'}),
        name='collections-detail'
    ),

    # NOTE: Using path instead of SimpleRouter because SimpleRouter expects retrieve
    # to look up values with an ID
    path(
        'me/',
        viewsets.CurrentUserViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='me'
    )
]
