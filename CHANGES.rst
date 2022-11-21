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

4.4.5 (2022-11-21)
==================

No significant changes.


----


4.4.4 (2022-07-26)
Bugfixes
--------

- Update pulpcore.
  `AAH-1202 <https://issues.redhat.com/browse/AAH-1202>`_
- Combine copy and remove tasks into single task
  `AAH-1349 <https://issues.redhat.com/browse/AAH-1349>`_
- Ensure that container remotes exclude source images by default to prevent networking errors when syncing.
  `AAH-1557 <https://issues.redhat.com/browse/AAH-1557>`_
- Use v3/excludes to exclude content from sync
  `AAH-1583 <https://issues.redhat.com/browse/AAH-1583>`_
- Fix persisting artifacts in collection deletion
  `AAH-1749 <https://issues.redhat.com/browse/AAH-1749>`_
- Forbid user with change_user perms to update superuser
  `AAH-1791 <https://issues.redhat.com/browse/AAH-1791>`_


Misc
----

- `AAH-1737 <https://issues.redhat.com/browse/AAH-1737>`_


----


4.4.3 (2022-03-16)
Bugfixes
--------

- Update to the latest pulp_container release
  `AAH-1373 <https://issues.redhat.com/browse/AAH-1373>`_
- Make sure orphan_protection_time is not set to zero
  `AAH-1384 <https://issues.redhat.com/browse/AAH-1384>`_
- Prevent artifact removal from latest version when deleting images
  `AAH-1389 <https://issues.redhat.com/browse/AAH-1389>`_
- Fix intermittent 500 when pulling execution environments.
  `AAH-1400 <https://issues.redhat.com/browse/AAH-1400>`_
- Fix intermittent 500 when pushing execution environments.
  `AAH-1411 <https://issues.redhat.com/browse/AAH-1411>`_


----


4.4.2 (2022-03-01)
Bugfixes
--------

- Log query items to api access log to capture collection details when uploading a collection.
  `AAH-1018 <https://issues.redhat.com/browse/AAH-1018>`_
- Update pulpcore to 3.15.4 to pickup CDN related fixes
  `AAH-1202 <https://issues.redhat.com/browse/AAH-1202>`_
- Update pulp_ansible to 0.10.2 to pickup proxy authentication fix.
  `AAH-1243 <https://issues.redhat.com/browse/AAH-1243>`_
- Add missing proxy_password if field is set on CollectionRemote update
  `AAH-1254 <https://issues.redhat.com/browse/AAH-1254>`_


----


4.4.1 (2022-01-06)
Bugfixes
--------

- Remote registry sync status not shown on registry page
  `AAH-1094 <https://issues.redhat.com/browse/AAH-1094>`_
- Upgrade to pulp-container 2.8.3 to fix azure and S3 storage backends.
  `AAH-1188 <https://issues.redhat.com/browse/AAH-1188>`_
- Fix a bug preventing users upgrading from 1.2 to 2.1 from downloading content from the rh-certified repository.
  `AAH-1200 <https://issues.redhat.com/browse/AAH-1200>`_


Misc
----

- `AAH-804 <https://issues.redhat.com/browse/AAH-804>`_, `AAH-1015 <https://issues.redhat.com/browse/AAH-1015>`_


----


4.4.0 (2021-11-18)
==================

Features
--------

- Update settings.py with Redis config provided by Clowder
  `AAH-382 <https://issues.redhat.com/browse/AAH-382>`_
- Create new api endpoints for listing, getting, and updating container registries.
  `AAH-434 <https://issues.redhat.com/browse/AAH-434>`_
- Create new api endpoints for listing, getting, and updating container remotes.
  `AAH-435 <https://issues.redhat.com/browse/AAH-435>`_
- Create remote sync api endpoint.
  `AAH-438 <https://issues.redhat.com/browse/AAH-438>`_
- Create templates to deploy Automation Hub services via the Clowder operator
  `AAH-581 <https://issues.redhat.com/browse/AAH-581>`_
- Start deploying galaxy_ng to ephemeral environments in pr_check
  `AAH-582 <https://issues.redhat.com/browse/AAH-582>`_
- Update to galaxy-importer version that uses ansible-core 2.11
  `AAH-588 <https://issues.redhat.com/browse/AAH-588>`_
- Add new healthz endpoint for liveness probe to check in ephemeral environments.
  `AAH-683 <https://issues.redhat.com/browse/AAH-683>`_
- Ensure retain_repo_versions=1 is set for newly created repositories and existing
  `AAH-708 <https://issues.redhat.com/browse/AAH-708>`_
- Enable Namespace deletion endpoint.
  `AAH-709 <https://issues.redhat.com/browse/AAH-709>`_
- Allow collection versions to be deleted
  `AAH-710 <https://issues.redhat.com/browse/AAH-710>`_
- Allow collections to be deleted
  `AAH-711 <https://issues.redhat.com/browse/AAH-711>`_
- Allow container repository to be deleted
  `AAH-712 <https://issues.redhat.com/browse/AAH-712>`_
- Allow container manifest to be deleted
  `AAH-713 <https://issues.redhat.com/browse/AAH-713>`_
- Add configuration for api access logging.
  `AAH-733 <https://issues.redhat.com/browse/AAH-733>`_
- Add unix socket support to collection version download view
  `AAH-743 <https://issues.redhat.com/browse/AAH-743>`_
- Update settings.py and urls.py with Social Auth values when environment is configured
  `AAH-846 <https://issues.redhat.com/browse/AAH-846>`_
- Add the ability to index execution environments from Red Hat registry remotes. This scans the registry for containers that are labeled with the execution environment label and creates remote container repositories for them which can be synced.
  `AAH-864 <https://issues.redhat.com/browse/AAH-864>`_
- Enable unauthenticated view-only collection browsing
  `AAH-881 <https://issues.redhat.com/browse/AAH-881>`_
- Add CONNECTED_ANSIBLE_CONTROLLERS setting which enables users to specify a list of controller instances that they wish to have galaxy ng connect to.
  `AAH-888 <https://issues.redhat.com/browse/AAH-888>`_
- Create access policy for registries endpoint.
  `AAH-896 <https://issues.redhat.com/browse/AAH-896>`_
- Create filters for container registries endpoint.
  `AAH-897 <https://issues.redhat.com/browse/AAH-897>`_
- Enable basic (username/password) authentication for galaxy apis.
  `AAH-901 <https://issues.redhat.com/browse/AAH-901>`_
- Add dependency filter to ui collection versions endpoint
  `AAH-902 <https://issues.redhat.com/browse/AAH-902>`_
- Add api endpoint for getting a listof tags in a container repository.
  `AAH-906 <https://issues.redhat.com/browse/AAH-906>`_
- Enable keycloak authentication using username and password for podman login.
  `AAH-916 <https://issues.redhat.com/browse/AAH-916>`_
- Add pre-authorized-redirect content guard to distributions
  `AAH-923 <https://issues.redhat.com/browse/AAH-923>`_
- Allow container registry-remote to be deleted
  `AAH-931 <https://issues.redhat.com/browse/AAH-931>`_
- Add created_at and updated_at filters to container registries endpoint.
  `AAH-938 <https://issues.redhat.com/browse/AAH-938>`_
- Add api endpoint to sync all remotes in a container registry.
  `AAH-945 <https://issues.redhat.com/browse/AAH-945>`_
- Add image manifests to container images api.
  `AAH-964 <https://issues.redhat.com/browse/AAH-964>`_


Bugfixes
--------

- Made API Root view to raise 404 if distro path is provided but distro doesn´t exist.
  `AAH-157 <https://issues.redhat.com/browse/AAH-157>`_
- Disable streamed sync endpoints
  `AAH-224 <https://issues.redhat.com/browse/AAH-224>`_
- Improve errors for max length violations in collection filename import
  `AAH-428 <https://issues.redhat.com/browse/AAH-428>`_
- Uses optional file_url from caller, pulp-ansible>=0.8, to support additional pulp backend storage platforms
  `AAH-431 <https://issues.redhat.com/browse/AAH-431>`_
- Fix incorrect openapi.yml

  Fix in this case mostly means removing an
  out of date version in lieu of the autogenerated
  version at /api/automation-hub/v3/openapi.yaml
  `AAH-450 <https://issues.redhat.com/browse/AAH-450>`_
- Fix "CVE-2021-32052 django: header injection" by moving to django ~=2.2.23
  `AAH-583 <https://issues.redhat.com/browse/AAH-583>`_
- Fix synclist to exclude all versions of un-checked collection.
  `AAH-585 <https://issues.redhat.com/browse/AAH-585>`_
- Update the required django to ~=2.2.23
  `AAH-601 <https://issues.redhat.com/browse/AAH-601>`_
- Pin 'click' version to 7.1.2 for 'rq' compat
  `AAH-637 <https://issues.redhat.com/browse/AAH-637>`_
- Implemented filters for state and keywords on imports API.
  `AAH-646 <https://issues.redhat.com/browse/AAH-646>`_
- Download collection artifacts from the galaxy apis instead of the pulp content app.
  `AAH-661 <https://issues.redhat.com/browse/AAH-661>`_
- Update to work with pulpcore 3.14 API
  `AAH-706 <https://issues.redhat.com/browse/AAH-706>`_
- Create 'inbound-namespaces' whenever a namespace is created.
  `AAH-739 <https://issues.redhat.com/browse/AAH-739>`_
- Fix typo in AWS S3 configuration for Clowder
  `AAH-781 <https://issues.redhat.com/browse/AAH-781>`_
- Fixed missing galaxy-importer configuration in Clowder template.
  `AAH-815 <https://issues.redhat.com/browse/AAH-815>`_
- Adds dependency django-automated-logging
  `AAH-849 <https://issues.redhat.com/browse/AAH-849>`_
- Fix keycloak setting not being loaded from /etc/pulp/settings.py
  `AAH-915 <https://issues.redhat.com/browse/AAH-915>`_
- Bump django-automated-logging version to include IP Address in logs
  `AAH-918 <https://issues.redhat.com/browse/AAH-918>`_
- Download collection artifacts from the pulp content app instead of the galaxy apis
  `AAH-924 <https://issues.redhat.com/browse/AAH-924>`_
- Fix container pull error to make compatible with drf-access-policy update
  `AAH-940 <https://issues.redhat.com/browse/AAH-940>`_
- Add auth_provider to users/ endpoint to denote an SSO user
  `AAH-952 <https://issues.redhat.com/browse/AAH-952>`_
- Add get_object to ContainerSyncRemoteView to fix AAH-989
  `AAH-989 <https://issues.redhat.com/browse/AAH-989>`_
- Allow deleting execution environment repositories with a dot in name
  `AAH-1049 <https://issues.redhat.com/browse/AAH-1049>`_
- Fix a bug where remote container repositories could not be deleted.
  `AAH-1095 <https://issues.redhat.com/browse/AAH-1095>`_


Misc
----

- `AAH-224 <https://issues.redhat.com/browse/AAH-224>`_, `AAH-424 <https://issues.redhat.com/browse/AAH-424>`_, `AAH-460 <https://issues.redhat.com/browse/AAH-460>`_, `AAH-563 <https://issues.redhat.com/browse/AAH-563>`_, `AAH-570 <https://issues.redhat.com/browse/AAH-570>`_, `AAH-576 <https://issues.redhat.com/browse/AAH-576>`_, `AAH-579 <https://issues.redhat.com/browse/AAH-579>`_, `AAH-581 <https://issues.redhat.com/browse/AAH-581>`_, `AAH-584 <https://issues.redhat.com/browse/AAH-584>`_, `AAH-603 <https://issues.redhat.com/browse/AAH-603>`_, `AAH-606 <https://issues.redhat.com/browse/AAH-606>`_, `AAH-647 <https://issues.redhat.com/browse/AAH-647>`_, `AAH-707 <https://issues.redhat.com/browse/AAH-707>`_, `AAH-750 <https://issues.redhat.com/browse/AAH-750>`_, `AAH-799 <https://issues.redhat.com/browse/AAH-799>`_, `AAH-830 <https://issues.redhat.com/browse/AAH-830>`_, `AAH-837 <https://issues.redhat.com/browse/AAH-837>`_, `AAH-871 <https://issues.redhat.com/browse/AAH-871>`_, `AAH-873 <https://issues.redhat.com/browse/AAH-873>`_, `AAH-917 <https://issues.redhat.com/browse/AAH-917>`_


----


4.3.0a2 (2021-04-16)
====================

Features
--------

- Enable OpenAPI spec at cloud.redhat.com/api/automation-hub/v3/openapi.json

  Update docs and decorators on viewsets and serializers to generate correct
  spec.

  Modify pulpcore openapigenerator to include concrete hrefs in addition
  to {ansible_collection_href}/ style endpoints.

  Need to provide the existing pulp /pulp/api/v3/docs/ view and
  a new view at /api/automation-hub/v3/openapi.json
  - new viewset may need drf-spectacular tweaks

  Sub tasks:
  - Create a snapshot of the OpenAPI spec in CI.
    - setup any useful tooling for validating/verifying the spec
      - openapidiff ?
  - Enable swaggerui view (/v3/swagger/ ?)

  Potential problems:

  - May want/need to import pulpcore openapi generator utils, which may not be in plugin
  api

  Before:

  Pulp uses drf-spectacular

  A "live" generated version of the API is available at

  http://localhost:5001/pulp/api/v3/docs/api.json
  http://localhost:5001/pulp/api/v3/docs/api.yaml

  And a "redoc" view at:
  http://localhost:5001/pulp/api/v3/docs/

  Note some issues:

  - Lots of endpoints are in the form "{ansible_collection_import_href}"
    - in theory, all endpoints should start with a "/" but even
    when evaluated, the above is "ansible/ansible/v3/collections/artifacts"

  - schema objects are inconsistent named
    - pulpcore has no prefix
    - pulp_ansible has ansible. prefix
    - galaxy_ng sometimes? has galaxy. prefix and sometimes Galaxy
  `AAH-57 <https://issues.redhat.com/browse/AAH-57>`_
- Add OpenShift job template to run database migrations
  `AAH-145 <https://issues.redhat.com/browse/AAH-145>`_
- Allow on to customize version for sdist building
  `AAH-185 <https://issues.redhat.com/browse/AAH-185>`_
- Add debug level logging about access_policy permission evaluation.
  `AAH-205 <https://issues.redhat.com/browse/AAH-205>`_
- Add unpaginated collections, collectionversions and metadata endopints for better sync performance.
  `AAH-224 <https://issues.redhat.com/browse/AAH-224>`_
- Add rate_limit to remotes api.
  `AAH-272 <https://issues.redhat.com/browse/AAH-272>`_
- Add container list and detail endpoints for execution environments.
  `AAH-274 <https://issues.redhat.com/browse/AAH-274>`_
- Add the ability to view the changes that have been made to a container repo.
  `AAH-276 <https://issues.redhat.com/browse/AAH-276>`_
- Add api to return images in a container repo.
  `AAH-277 <https://issues.redhat.com/browse/AAH-277>`_
- Set pulp container access policies.
  `AAH-278 <https://issues.redhat.com/browse/AAH-278>`_
- Load initial data for repo, remote and distribution using data migrations
  `AAH-281 <https://issues.redhat.com/browse/AAH-281>`_
- Add GALAXY_FEATURE_FLAGS to enable/disable execution environments
  `AAH-298 <https://issues.redhat.com/browse/AAH-298>`_
- Add the ability to create readmes for container distributions.
  `AAH-317 <https://issues.redhat.com/browse/AAH-317>`_
- Add api for loading a container manifest configuration blob.
  `AAH-338 <https://issues.redhat.com/browse/AAH-338>`_
- Add requires_ansible to the collection api endpoints
  `AAH-409 <https://issues.redhat.com/browse/AAH-409>`_
- Add models for container registry sync config
  `AAH-432 <https://issues.redhat.com/browse/AAH-432>`_
- Allow creating super users.
  `AAH-500 <https://issues.redhat.com/browse/AAH-500>`_


Bugfixes
--------

- Fix how travis checks for existence of Jira issues
  `AAH-44 <https://issues.redhat.com/browse/AAH-44>`_
- Fixed synclist curation creating 2 * N tasks, where N is number of synclists.
  Now synclist curation is executed in batches. Number of batches is configured in project settings.
  By default it is set to 200 synclists per task.
  `AAH-50 <https://issues.redhat.com/browse/AAH-50>`_
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
- Fix the galaxy-importer check for max size of docs files
  `AAH-220 <https://issues.redhat.com/browse/AAH-220>`_
- Only show synclist toggles to org admin.


  ie, non org admin's should get 403 response
  when viewing synclist endpoints.
  `AAH-222 <https://issues.redhat.com/browse/AAH-222>`_
- Users should not be able to delete themselves.

  Even if they have 'delete-user' perms.
  `AAH-265 <https://issues.redhat.com/browse/AAH-265>`_
- Prevent users with delete-user perms from deleting admin users
  `AAH-266 <https://issues.redhat.com/browse/AAH-266>`_
- Make token and password obfuscated on the API docs for /sync/config
  `AAH-282 <https://issues.redhat.com/browse/AAH-282>`_
- split proxy_url in 3 fields: username, password, address
  `AAH-291 <https://issues.redhat.com/browse/AAH-291>`_
- Fix groups endpoint viewable only by admin
  `AAH-453 <https://issues.redhat.com/browse/AAH-453>`_
- Expose pulp API in generated openapi spec.
  `AAH-482 <https://issues.redhat.com/browse/AAH-482>`_
- Replace current PULP_REDIS* env variables with PULP_REDIS_URL env variable to accommodate PULP_REDIS_SSL.
  `AAH-486 <https://issues.redhat.com/browse/AAH-486>`_


Misc
----

- `AAH-16 <https://issues.redhat.com/browse/AAH-16>`_, `AAH-31 <https://issues.redhat.com/browse/AAH-31>`_, `AAH-120 <https://issues.redhat.com/browse/AAH-120>`_, `AAH-139 <https://issues.redhat.com/browse/AAH-139>`_, `AAH-176 <https://issues.redhat.com/browse/AAH-176>`_, `AAH-177 <https://issues.redhat.com/browse/AAH-177>`_, `AAH-257 <https://issues.redhat.com/browse/AAH-257>`_, `AAH-295 <https://issues.redhat.com/browse/AAH-295>`_, `AAH-299 <https://issues.redhat.com/browse/AAH-299>`_, `AAH-344 <https://issues.redhat.com/browse/AAH-344>`_, `AAH-387 <https://issues.redhat.com/browse/AAH-387>`_, `AAH-393 <https://issues.redhat.com/browse/AAH-393>`_, `AAH-425 <https://issues.redhat.com/browse/AAH-425>`_, `AAH-433 <https://issues.redhat.com/browse/AAH-433>`_, `AAH-478 <https://issues.redhat.com/browse/AAH-478>`_, `AAH-483 <https://issues.redhat.com/browse/AAH-483>`_


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
