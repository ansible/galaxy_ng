from pprint import pprint


def run():  # pragma: no cover
    """Start DAB Resource Sync"""
    from ansible_base.resource_registry.tasks.sync import SyncExecutor
    executor = SyncExecutor(retries=3)
    executor.run()
    pprint(executor.results)
