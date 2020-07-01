When subscribers modify their synclist or the upstream repository versions changes, update the synclist repos.

Add /curate/ endpoints to synclists (POST /_ui/my-synclists/{pk}/curate/) to trigger curating
a synclist repo.

Add /curate/ endpoints to repositories (POST /content/<repo_name>/v3/collections/curate/
to trigger updating all synclists repos whose upstream_repository points to
/content/<repo_name>/

Add new tasks:

* curate_synclist_repository(synclist_pk)
  * update synclist.repository based on synclist.policy, synclist.collections, and synclist.namespaces
* curate_all_synclist_repositoies(upstream_repository_name)
  * Create a TaskGroup and create a curate_synclist_repository subtask for each synclist repo
  * Also creates a GroupProgressReport for the TaskGroup
    * Could be used to surface promotion status in UI

Note: When using curate_all_synclist_repositoies with a lot of synclist repositories, it is
recommended to enable multiple pulp workers.

For example, if using the galaxy_ng dev docker-compose tools:

    $ ./compose up --scale worker=2
