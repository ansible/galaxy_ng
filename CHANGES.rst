=========
Changelog
=========

..
    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.
    To add a new change log entry, please see
    https://docs.pulpproject.org/en/3.0/nightly/contributing/git.html#changelog-update

    WARNING: Don't drop the next directive!

.. towncrier release notes start

4.2.1 (2020-12-16)
==================

Bugfixes
--------

- Fix NamespaceLink creation and Validation on duplicated name.
  `AAH-132 <https://issues.redhat.com/browse/AAH-132>`_
- API returns 409 in case of existing group with same name.
  `AAH-152 <https://issues.redhat.com/browse/AAH-152>`_
- The namespaces api now performs a partial match on namespace name and namespace company name when using the 'keywords' query parameter.
  `AAH-166 <https://issues.redhat.com/browse/AAH-166>`_
- Fix KeyError lookup in namespace and collection viewset
  `AAH-195 <https://issues.redhat.com/browse/AAH-195>`_
- Fix error in error msg when importing invalid filenames
  `AAH-203 <https://issues.redhat.com/browse/AAH-203>`_


Misc
----

- `AAH-139 <https://issues.redhat.com/browse/AAH-139>`_, `AAH-176 <https://issues.redhat.com/browse/AAH-176>`_, `AAH-177 <https://issues.redhat.com/browse/AAH-177>`_


----


4.2.0 (2020-11-12)
==================

Bugfixes
--------

- Fix URLs in remote fixtures for correct validation.
  `AAH-12 <https://issues.redhat.com/browse/AAH-12>`_
- Fix importer running ansible-test in local image build
  `AAH-89 <https://issues.redhat.com/browse/AAH-89>`_
- Fix my-synclist to show only synclists with obj permissions
  `AAH-97 <https://issues.redhat.com/browse/AAH-97>`_


Misc
----

- `AAH-131 <https://issues.redhat.com/browse/AAH-131>`_


----


4.2.0rc3 (2020-11-04)
=====================

Bugfixes
--------

- Add deprecated annotated field to empty queryset
  `AAH-122 <https://issues.redhat.com/browse/AAH-122>`_


----


4.2.0rc2 (2020-11-02)
=====================

Features
--------

- Support pulp_ansible collection deprecation edits
  `AAH-76 <https://issues.redhat.com/browse/AAH-76>`_
- Add staging and rejected repos via migration and remove from dev fixture
  `#485 <https://github.com/ansible/galaxy_ng/issues/485>`_


Bugfixes
--------

- Update error messages on namespace links so that they can be differentiated from error messages on namespaces.
  `AAH-18 <https://issues.redhat.com/browse/AAH-18>`_
- Fix my-distributions show only sycnlist distros with obj perms
  `AAH-27 <https://issues.redhat.com/browse/AAH-27>`_
- Fix sort=created on ui /imports/collections/
  `AAH-98 <https://issues.redhat.com/browse/AAH-98>`_
- Fix `"CollectionImport.task_id" must be a "CollectionImport" instance.` errors on import task.
  `AAH-99 <https://issues.redhat.com/browse/AAH-99>`_


Misc
----

- `AAH-17 <https://issues.redhat.com/browse/AAH-17>`_, `AAH-21 <https://issues.redhat.com/browse/AAH-21>`_, `AAH-26 <https://issues.redhat.com/browse/AAH-26>`_, `AAH-34 <https://issues.redhat.com/browse/AAH-34>`_, `AAH-44 <https://issues.redhat.com/browse/AAH-44>`_, `AAH-47 <https://issues.redhat.com/browse/AAH-47>`_, `AAH-81 <https://issues.redhat.com/browse/AAH-81>`_, `AAH-82 <https://issues.redhat.com/browse/AAH-82>`_, `AAH-90 <https://issues.redhat.com/browse/AAH-90>`_, `AAH-94 <https://issues.redhat.com/browse/AAH-94>`_, `AAH-105 <https://issues.redhat.com/browse/AAH-105>`_, `468 <https://github.com/ansible/galaxy_ng/issues/468>`_


----


4.2.0rc1 (2020-10-02)
=====================

Bugfixes
--------

- Make error return for upload filename parsing errors provides an error code 'invalid'
  `#31 <https://github.com/ansible/galaxy_ng/issues/31>`_
- Fixes missing collection documentation after syncing from cloud.redhat.com.
  `#441 <https://github.com/ansible/galaxy_ng/issues/441>`_
- Add missing RepositoryVersion to inbound repos created via migration
  `#493 <https://github.com/ansible/galaxy_ng/issues/493>`_
- On upload use filename namespace as distro when no distro specified
  `#496 <https://github.com/ansible/galaxy_ng/issues/496>`_


Misc
----

- `#390 <https://github.com/ansible/galaxy_ng/issues/390>`_, `#473 <https://github.com/ansible/galaxy_ng/issues/473>`_


----


4.2.0b3 (2020-09-24)
====================

Features
--------

- Allow a user to specify the protocol she wants to use to talk to the pulp backend. (ie. http vs. https)
  `#464 <https://github.com/ansible/galaxy_ng/issues/464>`_
- Upgrade to pulpcore 3.7.0 and allow for 3.8.0

  Based on the API stability guidance at
  https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/concepts/index.html#plugin-api-stability-and-deprecation-policy
  `#476 <https://github.com/ansible/galaxy_ng/issues/476>`_


Misc
----

- `#474 <https://github.com/ansible/galaxy_ng/issues/474>`_


----


4.2.0b2 (2020-09-16)
====================

Features
--------

- The task for curating content needs to be initiated whenever a new collection lands in the golden repository.
  `#428 <https://github.com/ansible/galaxy_ng/issues/428>`_


Bugfixes
--------

- Order remotes and distributions by name instead of last updated.
  `#445 <https://github.com/ansible/galaxy_ng/issues/445>`_


Misc
----

- `#430 <https://github.com/ansible/galaxy_ng/issues/430>`_, `#439 <https://github.com/ansible/galaxy_ng/issues/439>`_, `#449 <https://github.com/ansible/galaxy_ng/issues/449>`_, `#457 <https://github.com/ansible/galaxy_ng/issues/457>`_


----


4.2.0b1 (2020-09-11)
====================

Features
--------

- When subscribers modify their synclist or the golden repository versions changes, AH needs to add/remove content from the associated repositories.
  `#17 <https://github.com/ansible/galaxy_ng/issues/17>`_
- Configure and manage content sync and collection remotes
  `#22 <https://github.com/ansible/galaxy_ng/issues/22>`_
- Support auto-created inbound pulp repositories per namespace
  `#37 <https://github.com/ansible/galaxy_ng/issues/37>`_
- Migration to add repo and distro for existing namespaces
  `#38 <https://github.com/ansible/galaxy_ng/issues/38>`_
- Add OpenAPI spec for exposing pulp collection viewsets.
  `#93 <https://github.com/ansible/galaxy_ng/issues/93>`_
- After successful import move collection version from incoming repo to staging repo
  `#117 <https://github.com/ansible/galaxy_ng/issues/117>`_
- Remove v3 api CollectionVersion certified flag filter
  `#120 <https://github.com/ansible/galaxy_ng/issues/120>`_
- Move _ui/ to the same level as v3/ and add versions to it.
  `#225 <https://github.com/ansible/galaxy_ng/issues/225>`_
- Create default synclist and associated repository/distribution on login.
  `#264 <https://github.com/ansible/galaxy_ng/issues/264>`_
- When subscribers modify their synclist or the upstream repository versions changes, update the synclist repos.

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
  `#265 <https://github.com/ansible/galaxy_ng/issues/265>`_
- When creating a synclist, ensure that the curated repo and distribution exists, and create them if needed.
  `#267 <https://github.com/ansible/galaxy_ng/issues/267>`_
- Add endpoints to manage Content Sync for community and rh-certified repositories.
  `#282 <https://github.com/ansible/galaxy_ng/issues/282>`_
- API: Update org repositories when new collection version published

  For c.rh.c, when a collection version is promoted from the staging
  repository to the published repository, the subscriber org repositories
  must be updated with the new artifact.

  The promotion event has to:
      - Kick-off n number of tasks, where n is the number of synclist repos
  `#285 <https://github.com/ansible/galaxy_ng/issues/285>`_
- Add endpoint to get status of pulp tasks
  `#295 <https://github.com/ansible/galaxy_ng/issues/295>`_
- Implement RBAC.
  - Adds DRF Access Policy to control permissions on DRF viewsets
  - Adds Django Guardian for assigning permissions to objects
  `#303 <https://github.com/ansible/galaxy_ng/issues/303>`_
- Expose the pulp core groups api. Exposes:
  - _ui/groups/ for listing and creating groups
  - _ui/groups/<pk> for deleting groups
  - _ui/groups/<pk>/model-permissions for listing and adding permissions to groups
  - _ui/groups/<pk>/model-permissions/<pk> for removing permissions from groups
  - _ui/groups/<pk>/users/ for listing and adding users to groups
  - _ui/groups/<pk>/users/<pk> for removing users from groups
  `#304 <https://github.com/ansible/galaxy_ng/issues/304>`_
- Removal of existing permission system
  - Viewsets no longer check to see if the user is in the system:partner-engineers group to determine if the user is an admin.
  - Red Hat entitlements checks have been moved to DRF Access Policy
  - Existing permission classes have been removed and replaced with DRF Access Policy permission classes.
  `#305 <https://github.com/ansible/galaxy_ng/issues/305>`_
- Add relevant user permissions to the _ui/me/ api for the UI to use.
  `#306 <https://github.com/ansible/galaxy_ng/issues/306>`_
- Use pulp repos to denote approved content on auto-approval
  `#316 <https://github.com/ansible/galaxy_ng/issues/316>`_
- Added Dockerfile.rhel8 for building docker images based on RHEL8.
  `#362 <https://github.com/ansible/galaxy_ng/issues/362>`_
- On publish check if inbound repo allows publishing
  `#372 <https://github.com/ansible/galaxy_ng/issues/372>`_
- Pin to pulpcore 3.6.0, pulp-ansible 0.2.0 and pulp-container 2.0.0
  `#380 <https://github.com/ansible/galaxy_ng/issues/380>`_
- Adds assign-permission management command for associating permissions to a group
  `#389 <https://github.com/ansible/galaxy_ng/issues/389>`_
- Add `distributions` and `my-distributions` endpoints to the UI api.
  `#397 <https://github.com/ansible/galaxy_ng/issues/397>`_


Bugfixes
--------

- Fix PATCH on my-synclists
  `#269 <https://github.com/ansible/galaxy_ng/issues/269>`_
- Fixed bug in auto certification parameter check, that caused all submitted content being automatically approved.
  `#318 <https://github.com/ansible/galaxy_ng/issues/318>`_
- Update requirements to use latest git versions of pulp*
  `#330 <https://github.com/ansible/galaxy_ng/issues/330>`_
- Update uses of pulp_ansible import_collection tasks to use PulpTemporaryFile
  `#333 <https://github.com/ansible/galaxy_ng/issues/333>`_
- chillout check_pulpcore_imports for a bit
  `#387 <https://github.com/ansible/galaxy_ng/issues/387>`_
- Add docs_blob to v3 api for collection versions
  `#403 <https://github.com/ansible/galaxy_ng/issues/403>`_
- Create namespaces on content sync
  `#404 <https://github.com/ansible/galaxy_ng/issues/404>`_


Misc
----

- `#297 <https://github.com/ansible/galaxy_ng/issues/297>`_, `#349 <https://github.com/ansible/galaxy_ng/issues/349>`_


----


4.2.0a10 (2020-07-15)
=====================

Features
--------

- Release packages in sdist and wheel formats. Static assets are download and included automatically during package build process.
  `#275 <https://github.com/ansible/galaxy_ng/issues/275>`_


Misc
----

- `#288 <https://github.com/ansible/galaxy_ng/issues/288>`_


----


4.2.0a9 (2020-07-08)
====================

Features
--------

- Add synclist models and viewsets
  `#18 <https://github.com/ansible/galaxy_ng/issues/18>`_
- Add collection version move/ endpoint to move to and from repository
  `#41 <https://github.com/ansible/galaxy_ng/issues/41>`_
- Add synclist (blacklist/whitelist for currated sync repos) support
  `#46 <https://github.com/ansible/galaxy_ng/issues/46>`_
- Implement authentication API for local Automation Hub.
  `#77 <https://github.com/ansible/galaxy_ng/issues/77>`_
- Support config to auto-approve collection versions on import
  `#170 <https://github.com/ansible/galaxy_ng/issues/170>`_
- Namespace API is copied from UI to v3 and now is server at ``<prefix>/v3/namespace/``.
  ``<prefix>/v3/_ui/namespace/`` is left as is.
  The new ``<prefix>/v3/namespace/`` endpoint changes how 'groups' are serialized.
  `#180 <https://github.com/ansible/galaxy_ng/issues/180>`_
- Token API is moved from UI to v3 and now is served at ``<prefix>/v3/auth/token/``.
  Token API does not support ``GET`` method anymore, token is returned to client only once after creation.
  Add support of HTTP Basic authentication method to the Token API.
  `#187 <https://github.com/ansible/galaxy_ng/issues/187>`_
- Enable the UI to be run as a container along with the rest of the development environment
  `#217 <https://github.com/ansible/galaxy_ng/issues/217>`_
- Fix bug preventing links from being modified on namespaces.
  `#277 <https://github.com/ansible/galaxy_ng/issues/277>`_


Bugfixes
--------

- Fixed invalid authorization for root API endpoints
  `#108 <https://github.com/ansible/galaxy_ng/issues/108>`_
- Fixed galaxy-importer errors in galaxy_ng container environment
  `#110 <https://github.com/ansible/galaxy_ng/issues/110>`_
- Fixed collection version detail endpoint returning invalid format of a `collection` field.
  `#113 <https://github.com/ansible/galaxy_ng/issues/113>`_
- Fix importer job scheduling issues with importer resource params
  `#122 <https://github.com/ansible/galaxy_ng/issues/122>`_
- Fix importer exception on unexpected docstring format
  `#159 <https://github.com/ansible/galaxy_ng/issues/159>`_
- Fix CollectionVersionViewSet so it filters based on "certification" status.
  `#214 <https://github.com/ansible/galaxy_ng/issues/214>`_
- Fix compose file name mismatch. In fixture data associate admin user with system:partner-engineers group.
  `#233 <https://github.com/ansible/galaxy_ng/issues/233>`_
- Fix wrong href's in results from collection viewsets
  `#247 <https://github.com/ansible/galaxy_ng/issues/247>`_
- Add back workaround for multipart forms from ansible-galaxy.
  `#256 <https://github.com/ansible/galaxy_ng/issues/256>`_


Misc
----

- `#118 <https://github.com/ansible/galaxy_ng/issues/118>`_, `#130 <https://github.com/ansible/galaxy_ng/issues/130>`_, `#131 <https://github.com/ansible/galaxy_ng/issues/131>`_, `#205 <https://github.com/ansible/galaxy_ng/issues/205>`_, `#209 <https://github.com/ansible/galaxy_ng/issues/209>`_, `#276 <https://github.com/ansible/galaxy_ng/issues/276>`_


----
