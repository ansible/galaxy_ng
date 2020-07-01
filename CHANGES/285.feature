API: Update org repositories when new collection version published

For c.rh.c, when a collection version is promoted from the staging
repository to the published repository, the subscriber org repositories
must be updated with the new artifact.

The promotion event has to:
    - Kick-off n number of tasks, where n is the number of synclist repos

