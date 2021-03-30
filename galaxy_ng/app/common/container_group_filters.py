from django.db.models import Q

CONTAINER_GROUPS = (
    'container.distribution',
    'container.namespace',
)


def exclude_container_groups(qs):
    for pattern in CONTAINER_GROUPS:
        qs = qs.exclude(name__startswith=pattern)
    return qs


def get_container_groups(qs):
    filter = Q()
    for pattern in CONTAINER_GROUPS:
        filter.add(Q(name__startswith=pattern), Q.OR)
    return qs.filter(filter)
