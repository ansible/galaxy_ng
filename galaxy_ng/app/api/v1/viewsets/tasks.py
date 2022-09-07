import datetime
import logging

from django.shortcuts import get_object_or_404

from rest_framework.decorators import action
from rest_framework.response import Response

from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api.v1.models import LegacyTask


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

    def legacy_task_hash(self, pulp_id):
        """Transform a uuid into an integer."""
        return abs(hash(str(pulp_id)))

    def legacy_dispatch(self, function, kwargs=None):
        """Dispatch wrapper for legacy tasks."""
        task = dispatch(function, kwargs=kwargs)
        hashed = self.legacy_task_hash(task.pulp_id)

        # add this task to the translation table
        legacy_task, _ = LegacyTask.objects.get_or_create(task_id=hashed, pulp_task=task)

        return hashed

    @action(detail=True, methods=['get'], name="Get task")
    def get_task(self, request, id=None):
        """Get a pulp task via the transformed v1 integer task id."""
        if id:
            task_id = id
        else:
            task_id = int(request.GET.get('id', None))

        # get the pulp task from the translation table
        legacy_task = get_object_or_404(LegacyTask, task_id=task_id)
        this_task = legacy_task.pulp_task

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
