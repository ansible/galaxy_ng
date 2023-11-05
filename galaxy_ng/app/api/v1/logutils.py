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

        legacyrole_import = LegacyRoleImport.objects.get(task=Task.current().pulp_id)
        legacyrole_import.add_log_record(record)
        legacyrole_import.save()
