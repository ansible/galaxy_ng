import logging


class LegacyRoleImportHandler(logging.Handler):
    """Logging handler for legacy role imports using galaxy-importer."""

    def emit(self, record: logging.LogRecord):
        """
        Store the log record into the `LegacyRoleImport.logs` field of the current task.
        """
        from .models import LegacyRoleImport
        from pulpcore.plugin.models import Task

        legacy_role_import = LegacyRoleImport.objects.get(task=Task.current().pulp_id)
        legacy_role_import.add_log_record(record)
        legacy_role_import.save()
