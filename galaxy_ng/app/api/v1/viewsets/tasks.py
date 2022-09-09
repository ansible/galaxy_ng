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
        return legacy_id

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
        msg_type = msg_type_map.get(state, state)

        # generate a message for the response
        msg = ''
        if state == 'SUCCESS':
            msg = 'role imported successfully'
        elif state == 'RUNNING':
            msg = 'running'
        if this_task.error:
            if this_task.error.get('traceback'):
                msg = (
                    this_task.error['description']
                    + '\n'
                    + this_task.error['traceback']
                )

        return Response({'results': [
            {
                'state': state,
                'id': task_id,
                'summary_fields': {
                    'task_messages': [{
                        'id': datetime.datetime.now().isoformat(),
                        'message_text': msg,
                        'message_type': msg_type,
                        'state': state
                    }]
                }
            }
        ]})
