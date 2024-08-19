import django_filters
from django_filters import filters

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.auth import Group
from galaxy_ng.app.models.organization import Organization
from galaxy_ng.app.models.organization import Team


class UserViewFilter(django_filters.FilterSet):

    sort = filters.OrderingFilter(
        fields=(
            ('username', 'username'),
            ('email', 'email'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('date_joined', 'date_joined')
        )
    )

    class Meta:
        model = User
        fields = {
            'username': ['exact', 'icontains', 'contains', 'startswith'],
            'email': ['exact', 'contains', 'startswith'],
            'first_name': ['exact', 'contains', 'startswith'],
            'last_name': ['exact', 'contains', 'startswith'],
            'date_joined': ['exact'],
            'resource__ansible_id': ['exact'],
            'is_superuser': ['exact'],
        }


class GroupViewFilter(django_filters.FilterSet):

    class Meta:
        model = Group
        fields = ["name"]


class OrganizationFilter(django_filters.FilterSet):
    resource__ansible_id = django_filters.CharFilter(
        field_name="resource__ansible_id", lookup_expr="exact"
    )

    class Meta:
        model = Organization
        fields = [
            "resource__ansible_id",
            "name",
        ]


class TeamFilter(django_filters.FilterSet):
    resource__ansible_id = django_filters.CharFilter(
        field_name="resource__ansible_id", lookup_expr="exact"
    )

    name__contains = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains"
    )

    name__icontains = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains"
    )

    class Meta:
        model = Team
        fields = [
            "resource__ansible_id",
            "name",
            "name__contains",
            "name__icontains"
        ]
