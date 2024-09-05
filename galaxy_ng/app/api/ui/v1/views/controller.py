from django.conf import settings
from rest_framework.permissions import IsAuthenticated

from galaxy_ng.app.api import base as api_base


class ControllerListView(api_base.APIView):
    permission_classes = [IsAuthenticated]

    # Returns a paginated list. This will make this easier to upgrade to a
    # database setting down the line.
    def get(self, request, *args, **kwargs):
        host_filter = request.GET.get("host", None)
        host_icontains_filter = request.GET.get("host__icontains", None)

        controllers = []
        for controller in settings.CONNECTED_ANSIBLE_CONTROLLERS:
            if host_filter and controller != host_filter:
                continue

            if host_icontains_filter and host_icontains_filter.lower() not in controller.lower():
                continue

            controllers.append({"host": controller})
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(controllers, request, view=self)

        return paginator.get_paginated_response(page)
