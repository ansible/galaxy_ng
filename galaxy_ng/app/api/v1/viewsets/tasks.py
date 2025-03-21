import datetime
import logging

from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema

from rest_framework.response import Response

from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.models import Task

from galaxy_ng.app.utils.galaxy import (
    uuid_to_int,
    int_to_uuid
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyTaskQuerySerializer,
    LegacyTaskDetailSerializer
)
from galaxy_ng.app.api.v1.models import LegacyRoleImport


logger = logging.getLogger(__name__)


class LegacyTasksMixin:
    """
    Legacy task helper.

    v1 task ids were integer values and have a different
    schema and states from the pulp tasking system.

    This set of functions will reshape a pulp task into
    something compatible with v1 clients such as the
    galaxy cli.
    """

    def legacy_dispatch(self, function, kwargs=None):
        """Dispatch wrapper for legacy tasks."""
        task = dispatch(function, kwargs=kwargs)
        legacy_id = uuid_to_int(str(task.pulp_id))
        return legacy_id, str(task.pulp_id)

    @extend_schema(
        parameters=[],
        request=LegacyTaskQuerySerializer(),
        responses=LegacyTaskDetailSerializer()
    )
    def get_task(self, request, id=None):
        """Get a pulp task via the transformed v1 integer task id."""
        if id:
            task_id = id
        else:
            task_id = int(request.GET.get('id', None))

        # get the pulp task from the translation table
        pulp_task_id = int_to_uuid(task_id)
        this_task = get_object_or_404(Task, pulp_id=pulp_task_id)

        # figure out the v1 compatible state
        state_map = {
            'COMPLETED': 'SUCCESS'
        }
        state = this_task.state.upper()
        state = state_map.get(state, state)

        # figure out the message type
        msg_type_map = {
            'RUNNING': 'INFO',
            'WAITING': 'INFO',
            'COMPLETED': 'SUCCESS'
        }

        task_messages = []

        # get messages from the model if this was a role import
        roleimport = LegacyRoleImport.objects.filter(task=this_task).first()
        if roleimport:
            for message in roleimport.messages:
                msg_type = msg_type_map.get(message['level'], message['level'])
                # FIXME(cutwater): The `datetime.utcfromtimestamp` method used here is a cause of
                #  multiple problems (deprecated method, naive-datetime object result,
                #  SonarCloud reliability issue). It returned a naive datetime object, which
                #  should be avoided in general. The recommended fix is to build
                #  a timezone-aware datetime object: `datetime.fromtimestamp(ts, timezone.utc)`.
                #  However to preserve current behavior we will return a naive object for now
                #  and revisit this code in future.
                ts = datetime.datetime.fromtimestamp(
                    message['time'], tz=datetime.timezone.utc
                ).replace(tzinfo=None).isoformat()
                msg_state = state_map.get(message['state'].upper(), message['state'].upper())
                msg = {
                    'id': ts,
                    'state': msg_state,
                    'message_type': msg_type,
                    'message_text': message['message']
                }
                task_messages.append(msg)

        return Response({'results': [
            {
                'state': state,
                'id': task_id,
                'summary_fields': {
                    'task_messages': task_messages
                }
            }
        ]})
