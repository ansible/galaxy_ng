import datetime
import logging

from rest_framework.decorators import action
from rest_framework.response import Response

from pulpcore.plugin.models import Task
from pulpcore.plugin.tasking import dispatch


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
        return hashed

    @action(detail=True, methods=['get'], name="Get task")
    def get_task(self, request, id=None):
        """Get a pulp task via the transformed v1 integer task id."""
        logger.debug(f'GET TASK: {request}')
        if id:
            task_id = id
        else:
            task_id = int(request.GET.get('id', None))
        logger.debug(f'GET TASK id: {task_id}')

        # iterate through most recent tasks to find the matching uuid
        this_task = None
        for t in Task.objects.all().order_by('started_at').reverse():
            tid = str(t.pulp_id)
            thash = self.legacy_task_hash(tid)
            if thash == task_id:
                this_task = t
                break

        logger.debug(f'FOUND TASK: {this_task} ..')

        # figure out the v1 compatible state
        state_map = {
            'COMPLETED': 'SUCCESS'
        }
        state = this_task.state.upper()
        state = state_map.get(state, state)

        # figure out the message type
        type_map = {
            'RUNNING': 'INFO',
            'WAITING': 'INFO',
            'COMPLETED': 'SUCCESS'
        }
        mtype = type_map.get(state, state)

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

        logger.debug(f'STATE:{state} MTYPE:{mtype}')
        return Response({'results': [
            {
                'state': state,
                'id': task_id,
                'summary_fields': {
                    'task_messages': [{
                        'id': datetime.datetime.now().isoformat(),
                        'message_text': msg,
                        'message_type': mtype,
                        'state': state
                    }]
                }
            }
        ]})
