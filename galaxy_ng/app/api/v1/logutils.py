import logging


class LegacyRoleImportHandler(logging.Handler):
    """
    A custom Handler which logs into `LegacyRoleImport.messages` attribute of the current task.
    """

    def emit(self, record):
        """
        Log `record` into the `LegacyRoleImport.messages` field of the current task.

        Args:
            record (logging.LogRecord): The record to log.

        """
        # This import cannot occur at import time because Django attempts to instantiate it early
        # which causes an unavoidable circular import as long as this needs to import any model
        from galaxy_ng.app.api.v1.models import LegacyRoleImport
        from pulpcore.plugin.models import Task

        # some v1 tasks may not create async jobs ...
        if not Task.current():
            return

        # v1 sync tasks will also end up here ...
        if not LegacyRoleImport.objects.filter(task=Task.current().pulp_id).exists():
            return

        # fetch the task
        task = Task.current()
        legacyrole_import = LegacyRoleImport.objects.get(task=task.pulp_id)
        legacyrole_import.add_log_record(record, state=task.state)
        legacyrole_import.save()
