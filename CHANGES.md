# Changelog

[//]: # (You should *NOT* be adding new change log entries to this file, this)
[//]: # (file is managed by towncrier. You *may* edit previous change logs to)
[//]: # (fix problems like typo corrections or such.)
[//]: # (To add a new change log entry, please see the contributing docs.)
[//]: # (WARNING: Don't drop the towncrier directive!)

[//]: # (towncrier release notes start)

## 4.10.0 (2024-09-19)

#### Bugfixes

- Support SVG avatar image on namespaces
  [#2836](https://github.com/ansible/galaxy_ng/issues/2836)
- Fixed issue where group members were also showing up as users in the Namespace owners list.
  [#3121](https://github.com/ansible/galaxy_ng/issues/3121)
- Parameterize ansible-test importer resource requirements
  [#3190](https://github.com/ansible/galaxy_ng/issues/3190)

#### Improved Documentation

- echo "add skeleton for galaxy_collection docs"
  [#2420](https://github.com/ansible/galaxy_ng/issues/2420)

#### Misc

- [#2822](https://github.com/ansible/galaxy_ng/issues/2822), [#3036](https://github.com/ansible/galaxy_ng/issues/3036), [#3064](https://github.com/ansible/galaxy_ng/issues/3064), [#3358](https://github.com/ansible/galaxy_ng/issues/3358), [#18825](https://github.com/ansible/galaxy_ng/issues/18825)


------------------------------------------------------------------------


## 4.9.0 (2023-12-06)

#### Features

-   Added management command
    [metrics-collection-automation-analytics]{.title-ref}. Renamed
    command [analytics-export-s3]{.title-ref} to
    [metrics-collection-lighspeed]{.title-ref}.
    [AA-1757](https://issues.redhat.com/browse/AA-1757)
-   Add support for dynamic settings
    [AAH-2009](https://issues.redhat.com/browse/AAH-2009)
-   Add \_ui/v1/tags/collections and \_ui/v1/tags/roles endpoints. Add
    sorting by name and count, and enable filtering by name (exact,
    partial and startswith match).
    [AAH-2761](https://issues.redhat.com/browse/AAH-2761)
-   Added `username_autocomplete` filter to `LegacyRole`.
    [AAH-2782](https://issues.redhat.com/browse/AAH-2782)

#### Bugfixes

-   Fix changing my namespace logo.
    [AAH-2296](https://issues.redhat.com/browse/AAH-2296)
-   Ensure beta-galaxy users can delete and deprecate their collections
    [AAH-2632](https://issues.redhat.com/browse/AAH-2632)
-   Add pulp_certs:/etc/pulp/certs volume to persist
    `database_fields.symmetric.key` and certificates on oci-env reload
    [AAH-2648](https://issues.redhat.com/browse/AAH-2648)
-   Fixed `username` filter in `/api/v1/users` endpoint.
    [AAH-2731](https://issues.redhat.com/browse/AAH-2731)
-   Fixed server error 500 on `/api/v1/namespaces` if browsable api is
    enabled [AAH-2733](https://issues.redhat.com/browse/AAH-2733)
-   Allow all authenticated users to list and retrieve other users when
    using github social auth.
    [AAH-2781](https://issues.redhat.com/browse/AAH-2781)

#### Misc

-   [AAH-2125](https://issues.redhat.com/browse/AAH-2125),
    [AAH-2148](https://issues.redhat.com/browse/AAH-2148),
    [AAH-2638](https://issues.redhat.com/browse/AAH-2638),
    [AAH-2760](https://issues.redhat.com/browse/AAH-2760),
    [AAH-2775](https://issues.redhat.com/browse/AAH-2775),
    [AAH-2802](https://issues.redhat.com/browse/AAH-2802)

------------------------------------------------------------------------

## 4.8.0 (2023-09-13)

#### Features

-   Keep a download count for legacy roles.
    [AAH-2238](https://issues.redhat.com/browse/AAH-2238)
-   Automate the process of updating translation files on a weekly
    basis. [AAH-2265](https://issues.redhat.com/browse/AAH-2265)
-   Fix publishing collection with ansible-galaxy when content approval
    si set to false.
    [AAH-2328](https://issues.redhat.com/browse/AAH-2328)
-   Add an oci-env community profile.
    [AAH-2382](https://issues.redhat.com/browse/AAH-2382)

#### Bugfixes

-   Fix container push update permission
    [AAH-2327](https://issues.redhat.com/browse/AAH-2327)
-   Decrease time for repo move tasks via pulp-ansible 0.17.2 x-repo
    improvement [AAH-2364](https://issues.redhat.com/browse/AAH-2364)
-   instructions to install legacy roles will now be accurate
    [AAH-2383](https://issues.redhat.com/browse/AAH-2383)
-   Set the correct pulp_type for the default collection remotes.
    [AAH-2385](https://issues.redhat.com/browse/AAH-2385)
-   Vendor django-automated-logging to provide Django 4.x compatibility
    [AAH-2388](https://issues.redhat.com/browse/AAH-2388)
-   Fix bug where namespace logos would fail to download with S3
    backends. [AAH-2575](https://issues.redhat.com/browse/AAH-2575)
-   Fix a bug where admin user\'s cannot cancel tasks.
    [AAH-2631](https://issues.redhat.com/browse/AAH-2631)

#### Misc

-   [AAH-2078](https://issues.redhat.com/browse/AAH-2078),
    [AAH-2125](https://issues.redhat.com/browse/AAH-2125),
    [AAH-2151](https://issues.redhat.com/browse/AAH-2151),
    [AAH-2213](https://issues.redhat.com/browse/AAH-2213),
    [AAH-2341](https://issues.redhat.com/browse/AAH-2341),
    [AAH-2343](https://issues.redhat.com/browse/AAH-2343),
    [AAH-2362](https://issues.redhat.com/browse/AAH-2362),
    [AAH-2393](https://issues.redhat.com/browse/AAH-2393),
    [AAH-2409](https://issues.redhat.com/browse/AAH-2409),
    [AAH-2415](https://issues.redhat.com/browse/AAH-2415),
    [AAH-2419](https://issues.redhat.com/browse/AAH-2419),
    [AAH-2442](https://issues.redhat.com/browse/AAH-2442),
    [AAH-2615](https://issues.redhat.com/browse/AAH-2615),
    [AAH-2654](https://issues.redhat.com/browse/AAH-2654)

------------------------------------------------------------------------

## 4.7.0 (2023-04-17)

#### Features

-   Promote execution environment APIs into the supported v3/ api
    [AAH-766](https://issues.redhat.com/browse/AAH-766)
-   Get AAP version from /etc/ansible-automation-platform/VERSION file
    [AAH-1315](https://issues.redhat.com/browse/AAH-1315)
-   Refactor permissions UI and API.
    [AAH-1714](https://issues.redhat.com/browse/AAH-1714)
-   Removed inbound repository logic
    [AAH-1777](https://issues.redhat.com/browse/AAH-1777)
-   Add limited v1 support for legacy roles specific for use in
    galaxy.ansible.com
    [AAH-1812](https://issues.redhat.com/browse/AAH-1812)
-   Added custom querysets to include/exclude private repositories from
    api results. [AAH-2000](https://issues.redhat.com/browse/AAH-2000)
-   Add version_range parameter to the \_ui/v1/collection-versions/
    endpoint. [AAH-2018](https://issues.redhat.com/browse/AAH-2018)
-   Removed repository lock during collection import
    [AAH-2104](https://issues.redhat.com/browse/AAH-2104)
-   Add GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS which configures LDAP to
    only add users into groups that already exist in the system.
    [AAH-2112](https://issues.redhat.com/browse/AAH-2112)
-   Add AI Index Deny List for Project Wisdom
    [AAH-2127](https://issues.redhat.com/browse/AAH-2127)
-   Updated endpoint
    `/v3/collections/{namespace}/{name}/versions/{version}/copy/{source_path}/{dest_path}/`
    to copy collection version with associated content
    [AAH-2149](https://issues.redhat.com/browse/AAH-2149)
-   Allow users to create and publish to custom staging and approved
    repos. [AAH-2170](https://issues.redhat.com/browse/AAH-2170)
-   Add support for namespace and logo sync.
    [AAH-2200](https://issues.redhat.com/browse/AAH-2200)

#### Bugfixes

-   Set no-cache headers of auth login endpoints
    [AAH-1323](https://issues.redhat.com/browse/AAH-1323)
-   Filter signatures scoped by distro.repository
    [AAH-1941](https://issues.redhat.com/browse/AAH-1941)
-   Add option to customize ldap group params
    [AAH-1957](https://issues.redhat.com/browse/AAH-1957)
-   Filtering deprecated EE from registry sync
    [AAH-1958](https://issues.redhat.com/browse/AAH-1958)
-   Fix AttributeError in index_registry task when handing serializer
    errors [AAH-1966](https://issues.redhat.com/browse/AAH-1966)
-   Update utility to avoid a JSONDecodeError
    [AAH-1975](https://issues.redhat.com/browse/AAH-1975)
-   Fix migration 0029 when upgrading from 4.2 to 4.6.
    [AAH-1994](https://issues.redhat.com/browse/AAH-1994)
-   Ensure that container deletion removes associated artifacts and
    content. [AAH-2024](https://issues.redhat.com/browse/AAH-2024)
-   Add content_guard to validated repo via migration
    [AAH-2038](https://issues.redhat.com/browse/AAH-2038)
-   Allow ldap.OPT_REFERRALS to be set
    [AAH-2150](https://issues.redhat.com/browse/AAH-2150)
-   Added access policy condition restricting access to the
    copy_collection_version endpoint
    [AAH-2223](https://issues.redhat.com/browse/AAH-2223)
-   Added access policy condition restricting access to the
    move_collection_version endpoint
    [AAH-2224](https://issues.redhat.com/browse/AAH-2224)

#### Misc

-   [AAH-805](https://issues.redhat.com/browse/AAH-805),
    [AAH-1270](https://issues.redhat.com/browse/AAH-1270),
    [AAH-1598](https://issues.redhat.com/browse/AAH-1598),
    [AAH-1612](https://issues.redhat.com/browse/AAH-1612),
    [AAH-1613](https://issues.redhat.com/browse/AAH-1613),
    [AAH-1672](https://issues.redhat.com/browse/AAH-1672),
    [AAH-1748](https://issues.redhat.com/browse/AAH-1748),
    [AAH-1797](https://issues.redhat.com/browse/AAH-1797),
    [AAH-1872](https://issues.redhat.com/browse/AAH-1872),
    [AAH-1911](https://issues.redhat.com/browse/AAH-1911),
    [AAH-1920](https://issues.redhat.com/browse/AAH-1920),
    [AAH-1950](https://issues.redhat.com/browse/AAH-1950),
    [AAH-1953](https://issues.redhat.com/browse/AAH-1953),
    [AAH-1956](https://issues.redhat.com/browse/AAH-1956),
    [AAH-1965](https://issues.redhat.com/browse/AAH-1965),
    [AAH-1985](https://issues.redhat.com/browse/AAH-1985),
    [AAH-1995](https://issues.redhat.com/browse/AAH-1995),
    [AAH-2001](https://issues.redhat.com/browse/AAH-2001),
    [AAH-2002](https://issues.redhat.com/browse/AAH-2002),
    [AAH-2003](https://issues.redhat.com/browse/AAH-2003),
    [AAH-2007](https://issues.redhat.com/browse/AAH-2007),
    [AAH-2029](https://issues.redhat.com/browse/AAH-2029),
    [AAH-2031](https://issues.redhat.com/browse/AAH-2031),
    [AAH-2033](https://issues.redhat.com/browse/AAH-2033),
    [AAH-2138](https://issues.redhat.com/browse/AAH-2138),
    [AAH-2279](https://issues.redhat.com/browse/AAH-2279),
    [AAH-2280](https://issues.redhat.com/browse/AAH-2280),
    [AAH-2281](https://issues.redhat.com/browse/AAH-2281),
    [AAH-2292](https://issues.redhat.com/browse/AAH-2292)

------------------------------------------------------------------------

4.6.0 (2022-10-13) Features \-\-\-\-\-\-\--

-   Change \'requires_ansible\' to use custom ansible ver spec instead
    of semver [AAH-981](https://issues.redhat.com/browse/AAH-981)
-   Allow signature upload, expose public_keys on API
    [AAH-1055](https://issues.redhat.com/browse/AAH-1055)
-   Add option to log collection downloads.
    [AAH-1118](https://issues.redhat.com/browse/AAH-1118)
-   Add Container Signing Service
    [AAH-1358](https://issues.redhat.com/browse/AAH-1358)
-   Output an error if no changelog.rst file is present in the root of
    the collection [AAH-1460](https://issues.redhat.com/browse/AAH-1460)
-   Changed import_collection to work off of a fileobject without
    requiring an filesystem entry
    [AAH-1506](https://issues.redhat.com/browse/AAH-1506)
-   Allow set of GALAXY_MINIMUM_PASSWORD_LENGTH for
    AUTH_PASSWORD_VALIDATORS
    [AAH-1531](https://issues.redhat.com/browse/AAH-1531)
-   Serve all collections at synclist distro, stop curation
    [AAH-1540](https://issues.redhat.com/browse/AAH-1540)
-   Serve the pulp api at /api/automation-hub/pulp/api/v3/
    [AAH-1544](https://issues.redhat.com/browse/AAH-1544)
-   Add LDAP integration
    [AAH-1593](https://issues.redhat.com/browse/AAH-1593)
-   Make /api/galaxy/pulp/api/v3/ part of the supported API.
    [AAH-1681](https://issues.redhat.com/browse/AAH-1681)
-   Add validated content repo.
    [AAH-1943](https://issues.redhat.com/browse/AAH-1943)

#### Bugfixes

-   Fixes forbidden message when installing from ansible-galaxy a public
    collection and the settings has enable unautheticated download.
    [AAH-1386](https://issues.redhat.com/browse/AAH-1386)
-   Fix 500 error when listing Group Roles
    [AAH-1595](https://issues.redhat.com/browse/AAH-1595)
-   Redirect requests from /pulp/api/v3/ to /api/galaxy/pulp/api/v3/.
    [AAH-1646](https://issues.redhat.com/browse/AAH-1646)
-   Fix feature flags for signing
    [AAH-1690](https://issues.redhat.com/browse/AAH-1690)
-   add signature upload statements
    [AAH-1700](https://issues.redhat.com/browse/AAH-1700)
-   Remove guardian foreign key contraints in rbac migration
    [AAH-1765](https://issues.redhat.com/browse/AAH-1765)
-   Allow roles assignment to group with [change_group]{.title-ref}
    permission [AAH-1766](https://issues.redhat.com/browse/AAH-1766)
-   Forbid user with change_user perms to update superuser
    [AAH-1791](https://issues.redhat.com/browse/AAH-1791)
-   Return only the sign state of the latest version of a collection.
    [AAH-1794](https://issues.redhat.com/browse/AAH-1794)
-   Remove conditional [view_task]{.title-ref}.
    [AAH-1805](https://issues.redhat.com/browse/AAH-1805)
-   Fix a bug preventing keycloak SSO users from logging in to the
    container registry with podman/docker login.
    [AAH-1921](https://issues.redhat.com/browse/AAH-1921)
-   Disable signatures in the v3 collection detail serializer
    [AAH-1937](https://issues.redhat.com/browse/AAH-1937)

#### Misc

-   [AAH-1092](https://issues.redhat.com/browse/AAH-1092),
    [AAH-1093](https://issues.redhat.com/browse/AAH-1093),
    [AAH-1127](https://issues.redhat.com/browse/AAH-1127),
    [AAH-1128](https://issues.redhat.com/browse/AAH-1128),
    [AAH-1360](https://issues.redhat.com/browse/AAH-1360),
    [AAH-1371](https://issues.redhat.com/browse/AAH-1371),
    [AAH-1443](https://issues.redhat.com/browse/AAH-1443),
    [AAH-1449](https://issues.redhat.com/browse/AAH-1449),
    [AAH-1468](https://issues.redhat.com/browse/AAH-1468),
    [AAH-1492](https://issues.redhat.com/browse/AAH-1492),
    [AAH-1493](https://issues.redhat.com/browse/AAH-1493),
    [AAH-1526](https://issues.redhat.com/browse/AAH-1526),
    [AAH-1530](https://issues.redhat.com/browse/AAH-1530),
    [AAH-1556](https://issues.redhat.com/browse/AAH-1556),
    [AAH-1585](https://issues.redhat.com/browse/AAH-1585),
    [AAH-1586](https://issues.redhat.com/browse/AAH-1586),
    [AAH-1587](https://issues.redhat.com/browse/AAH-1587),
    [AAH-1588](https://issues.redhat.com/browse/AAH-1588),
    [AAH-1589](https://issues.redhat.com/browse/AAH-1589),
    [AAH-1608](https://issues.redhat.com/browse/AAH-1608),
    [AAH-1609](https://issues.redhat.com/browse/AAH-1609),
    [AAH-1643](https://issues.redhat.com/browse/AAH-1643),
    [AAH-1654](https://issues.redhat.com/browse/AAH-1654),
    [AAH-1697](https://issues.redhat.com/browse/AAH-1697),
    [AAH-1712](https://issues.redhat.com/browse/AAH-1712),
    [AAH-1737](https://issues.redhat.com/browse/AAH-1737),
    [AAH-1738](https://issues.redhat.com/browse/AAH-1738),
    [AAH-1757](https://issues.redhat.com/browse/AAH-1757),
    [AAH-1768](https://issues.redhat.com/browse/AAH-1768),
    [AAH-1770](https://issues.redhat.com/browse/AAH-1770),
    [AAH-1780](https://issues.redhat.com/browse/AAH-1780),
    [AAH-1781](https://issues.redhat.com/browse/AAH-1781),
    [AAH-1788](https://issues.redhat.com/browse/AAH-1788),
    [AAH-1796](https://issues.redhat.com/browse/AAH-1796),
    [AAH-1821](https://issues.redhat.com/browse/AAH-1821),
    [AAH-1828](https://issues.redhat.com/browse/AAH-1828),
    [AAH-1846](https://issues.redhat.com/browse/AAH-1846),
    [AAH-1850](https://issues.redhat.com/browse/AAH-1850),
    [AAH-1906](https://issues.redhat.com/browse/AAH-1906),
    [AAH-1908](https://issues.redhat.com/browse/AAH-1908)

------------------------------------------------------------------------

## 4.5.0 (2022-05-04)

#### Features

-   Collection Signing, signature creation, upload, verification and
    APIs. [AAH-312](https://issues.redhat.com/browse/AAH-312)
-   Add Signing Service to the dev environment
    [AAH-1181](https://issues.redhat.com/browse/AAH-1181)
-   Update pulp_ansible to 0.12.0, for signing features
    [AAH-1353](https://issues.redhat.com/browse/AAH-1353)
-   Add \"related_fields\" to the namespace serializer, which can
    optionally return \"my_permissions\" for namespaces.
    [AAH-1458](https://issues.redhat.com/browse/AAH-1458)

#### Bugfixes

-   Improve queries on move api endpoint
    [AAH-692](https://issues.redhat.com/browse/AAH-692)
-   Log query items to api access log to capture collection details when
    uploading a collection.
    [AAH-1018](https://issues.redhat.com/browse/AAH-1018)
-   Remote registry sync status not shown on registry page
    [AAH-1094](https://issues.redhat.com/browse/AAH-1094)
-   Fix response for downloading collections in insights mode
    [AAH-1162](https://issues.redhat.com/browse/AAH-1162)
-   Upgrade to pulp-container 2.8.3 to fix azure and S3 storage
    backends. [AAH-1188](https://issues.redhat.com/browse/AAH-1188)
-   Fix a bug preventing users upgrading from 1.2 to 2.1 from
    downloading content from the rh-certified repository.
    [AAH-1200](https://issues.redhat.com/browse/AAH-1200)
-   Add missing proxy_password if field is set on CollectionRemote
    update [AAH-1254](https://issues.redhat.com/browse/AAH-1254)
-   Combine copy and remove tasks into single task
    [AAH-1349](https://issues.redhat.com/browse/AAH-1349)
-   Update to the latest pulp_container release
    [AAH-1373](https://issues.redhat.com/browse/AAH-1373)
-   Make sure orphan_protection_time is not set to zero
    [AAH-1384](https://issues.redhat.com/browse/AAH-1384)
-   Prevent artifact removal from latest version when deleting images
    [AAH-1389](https://issues.redhat.com/browse/AAH-1389)
-   Update locks on synclist tasks so golden_repo will not be written to
    during tasks [AAH-1395](https://issues.redhat.com/browse/AAH-1395)
-   Check for existing synclist obj before create in RH Auth
    [AAH-1399](https://issues.redhat.com/browse/AAH-1399)
-   Remove custom admin as TaskAdmin was removed from pulpcore
    [AAH-1478](https://issues.redhat.com/browse/AAH-1478)
-   Fix collectionversion query build, it was taking too much time to
    calculate a django Q() expression
    [AAH-1484](https://issues.redhat.com/browse/AAH-1484)
-   Use simple string splitting to remove the requirements versions
    [AAH-1545](https://issues.redhat.com/browse/AAH-1545)
-   Ensure that container remotes exclude source images by default to
    prevent networking errors when syncing.
    [AAH-1557](https://issues.redhat.com/browse/AAH-1557)

#### Misc

-   [AAH-765](https://issues.redhat.com/browse/AAH-765),
    [AAH-804](https://issues.redhat.com/browse/AAH-804),
    [AAH-1015](https://issues.redhat.com/browse/AAH-1015),
    [AAH-1038](https://issues.redhat.com/browse/AAH-1038),
    [AAH-1042](https://issues.redhat.com/browse/AAH-1042),
    [AAH-1090](https://issues.redhat.com/browse/AAH-1090),
    [AAH-1092](https://issues.redhat.com/browse/AAH-1092),
    [AAH-1097](https://issues.redhat.com/browse/AAH-1097),
    [AAH-1106](https://issues.redhat.com/browse/AAH-1106),
    [AAH-1212](https://issues.redhat.com/browse/AAH-1212),
    [AAH-1214](https://issues.redhat.com/browse/AAH-1214),
    [AAH-1219](https://issues.redhat.com/browse/AAH-1219),
    [AAH-1278](https://issues.redhat.com/browse/AAH-1278),
    [AAH-1361](https://issues.redhat.com/browse/AAH-1361),
    [AAH-1418](https://issues.redhat.com/browse/AAH-1418),
    [AAH-1442](https://issues.redhat.com/browse/AAH-1442)

------------------------------------------------------------------------

## 4.4.0 (2021-11-18)

#### Features

-   Update settings.py with Redis config provided by Clowder
    [AAH-382](https://issues.redhat.com/browse/AAH-382)
-   Create new api endpoints for listing, getting, and updating
    container registries.
    [AAH-434](https://issues.redhat.com/browse/AAH-434)
-   Create new api endpoints for listing, getting, and updating
    container remotes.
    [AAH-435](https://issues.redhat.com/browse/AAH-435)
-   Create remote sync api endpoint.
    [AAH-438](https://issues.redhat.com/browse/AAH-438)
-   Create templates to deploy Automation Hub services via the Clowder
    operator [AAH-581](https://issues.redhat.com/browse/AAH-581)
-   Start deploying galaxy_ng to ephemeral environments in pr_check
    [AAH-582](https://issues.redhat.com/browse/AAH-582)
-   Update to galaxy-importer version that uses ansible-core 2.11
    [AAH-588](https://issues.redhat.com/browse/AAH-588)
-   Add new healthz endpoint for liveness probe to check in ephemeral
    environments. [AAH-683](https://issues.redhat.com/browse/AAH-683)
-   Ensure retain_repo_versions=1 is set for newly created repositories
    and existing [AAH-708](https://issues.redhat.com/browse/AAH-708)
-   Enable Namespace deletion endpoint.
    [AAH-709](https://issues.redhat.com/browse/AAH-709)
-   Allow collection versions to be deleted
    [AAH-710](https://issues.redhat.com/browse/AAH-710)
-   Allow collections to be deleted
    [AAH-711](https://issues.redhat.com/browse/AAH-711)
-   Allow container repository to be deleted
    [AAH-712](https://issues.redhat.com/browse/AAH-712)
-   Allow container manifest to be deleted
    [AAH-713](https://issues.redhat.com/browse/AAH-713)
-   Add configuration for api access logging.
    [AAH-733](https://issues.redhat.com/browse/AAH-733)
-   Add unix socket support to collection version download view
    [AAH-743](https://issues.redhat.com/browse/AAH-743)
-   Update settings.py and urls.py with Social Auth values when
    environment is configured
    [AAH-846](https://issues.redhat.com/browse/AAH-846)
-   Add the ability to index execution environments from Red Hat
    registry remotes. This scans the registry for containers that are
    labeled with the execution environment label and creates remote
    container repositories for them which can be synced.
    [AAH-864](https://issues.redhat.com/browse/AAH-864)
-   Enable unauthenticated view-only collection browsing
    [AAH-881](https://issues.redhat.com/browse/AAH-881)
-   Add CONNECTED_ANSIBLE_CONTROLLERS setting which enables users to
    specify a list of controller instances that they wish to have galaxy
    ng connect to. [AAH-888](https://issues.redhat.com/browse/AAH-888)
-   Create access policy for registries endpoint.
    [AAH-896](https://issues.redhat.com/browse/AAH-896)
-   Create filters for container registries endpoint.
    [AAH-897](https://issues.redhat.com/browse/AAH-897)
-   Enable basic (username/password) authentication for galaxy apis.
    [AAH-901](https://issues.redhat.com/browse/AAH-901)
-   Add dependency filter to ui collection versions endpoint
    [AAH-902](https://issues.redhat.com/browse/AAH-902)
-   Add api endpoint for getting a listof tags in a container
    repository. [AAH-906](https://issues.redhat.com/browse/AAH-906)
-   Enable keycloak authentication using username and password for
    podman login. [AAH-916](https://issues.redhat.com/browse/AAH-916)
-   Add pre-authorized-redirect content guard to distributions
    [AAH-923](https://issues.redhat.com/browse/AAH-923)
-   Allow container registry-remote to be deleted
    [AAH-931](https://issues.redhat.com/browse/AAH-931)
-   Add created_at and updated_at filters to container registries
    endpoint. [AAH-938](https://issues.redhat.com/browse/AAH-938)
-   Add api endpoint to sync all remotes in a container registry.
    [AAH-945](https://issues.redhat.com/browse/AAH-945)
-   Add image manifests to container images api.
    [AAH-964](https://issues.redhat.com/browse/AAH-964)

#### Bugfixes

-   Made API Root view to raise 404 if distro path is provided but
    distro doesn´t exist.
    [AAH-157](https://issues.redhat.com/browse/AAH-157)

-   Disable streamed sync endpoints
    [AAH-224](https://issues.redhat.com/browse/AAH-224)

-   Improve errors for max length violations in collection filename
    import [AAH-428](https://issues.redhat.com/browse/AAH-428)

-   Uses optional file_url from caller, pulp-ansible\>=0.8, to support
    additional pulp backend storage platforms
    [AAH-431](https://issues.redhat.com/browse/AAH-431)

-   Fix incorrect openapi.yml

    Fix in this case mostly means removing an out of date version in
    lieu of the autogenerated version at
    /api/automation-hub/v3/openapi.yaml
    [AAH-450](https://issues.redhat.com/browse/AAH-450)

-   Fix \"CVE-2021-32052 django: header injection\" by moving to django
    \~=2.2.23 [AAH-583](https://issues.redhat.com/browse/AAH-583)

-   Fix synclist to exclude all versions of un-checked collection.
    [AAH-585](https://issues.redhat.com/browse/AAH-585)

-   Update the required django to \~=2.2.23
    [AAH-601](https://issues.redhat.com/browse/AAH-601)

-   Pin \'click\' version to 7.1.2 for \'rq\' compat
    [AAH-637](https://issues.redhat.com/browse/AAH-637)

-   Implemented filters for state and keywords on imports API.
    [AAH-646](https://issues.redhat.com/browse/AAH-646)

-   Download collection artifacts from the galaxy apis instead of the
    pulp content app.
    [AAH-661](https://issues.redhat.com/browse/AAH-661)

-   Update to work with pulpcore 3.14 API
    [AAH-706](https://issues.redhat.com/browse/AAH-706)

-   Create \'inbound-namespaces\' whenever a namespace is created.
    [AAH-739](https://issues.redhat.com/browse/AAH-739)

-   Fix typo in AWS S3 configuration for Clowder
    [AAH-781](https://issues.redhat.com/browse/AAH-781)

-   Fixed missing galaxy-importer configuration in Clowder template.
    [AAH-815](https://issues.redhat.com/browse/AAH-815)

-   Adds dependency django-automated-logging
    [AAH-849](https://issues.redhat.com/browse/AAH-849)

-   Fix keycloak setting not being loaded from /etc/pulp/settings.py
    [AAH-915](https://issues.redhat.com/browse/AAH-915)

-   Bump django-automated-logging version to include IP Address in logs
    [AAH-918](https://issues.redhat.com/browse/AAH-918)

-   Download collection artifacts from the pulp content app instead of
    the galaxy apis [AAH-924](https://issues.redhat.com/browse/AAH-924)

-   Fix container pull error to make compatible with drf-access-policy
    update [AAH-940](https://issues.redhat.com/browse/AAH-940)

-   Add auth_provider to users/ endpoint to denote an SSO user
    [AAH-952](https://issues.redhat.com/browse/AAH-952)

-   Add get_object to ContainerSyncRemoteView to fix AAH-989
    [AAH-989](https://issues.redhat.com/browse/AAH-989)

-   Allow deleting execution environment repositories with a dot in name
    [AAH-1049](https://issues.redhat.com/browse/AAH-1049)

-   Fix a bug where remote container repositories could not be deleted.
    [AAH-1095](https://issues.redhat.com/browse/AAH-1095)

#### Misc

-   [AAH-224](https://issues.redhat.com/browse/AAH-224),
    [AAH-424](https://issues.redhat.com/browse/AAH-424),
    [AAH-460](https://issues.redhat.com/browse/AAH-460),
    [AAH-563](https://issues.redhat.com/browse/AAH-563),
    [AAH-570](https://issues.redhat.com/browse/AAH-570),
    [AAH-576](https://issues.redhat.com/browse/AAH-576),
    [AAH-579](https://issues.redhat.com/browse/AAH-579),
    [AAH-581](https://issues.redhat.com/browse/AAH-581),
    [AAH-584](https://issues.redhat.com/browse/AAH-584),
    [AAH-603](https://issues.redhat.com/browse/AAH-603),
    [AAH-606](https://issues.redhat.com/browse/AAH-606),
    [AAH-647](https://issues.redhat.com/browse/AAH-647),
    [AAH-707](https://issues.redhat.com/browse/AAH-707),
    [AAH-750](https://issues.redhat.com/browse/AAH-750),
    [AAH-799](https://issues.redhat.com/browse/AAH-799),
    [AAH-830](https://issues.redhat.com/browse/AAH-830),
    [AAH-837](https://issues.redhat.com/browse/AAH-837),
    [AAH-871](https://issues.redhat.com/browse/AAH-871),
    [AAH-873](https://issues.redhat.com/browse/AAH-873),
    [AAH-917](https://issues.redhat.com/browse/AAH-917)

------------------------------------------------------------------------

## 4.3.0a2 (2021-04-16)

#### Features

-   Enable OpenAPI spec at
    cloud.redhat.com/api/automation-hub/v3/openapi.json

    Update docs and decorators on viewsets and serializers to generate
    correct spec.

    Modify pulpcore openapigenerator to include concrete hrefs in
    addition to {ansible_collection_href}/ style endpoints.

    Need to provide the existing pulp /pulp/api/v3/docs/ view and a new
    view at /api/automation-hub/v3/openapi.json

    -   new viewset may need drf-spectacular tweaks

    Sub tasks:

    -   Create a snapshot of the OpenAPI spec in CI.
        -   setup any useful tooling for validating/verifying the spec
            -   openapidiff ?
    -   Enable swaggerui view (/v3/swagger/ ?)

    Potential problems:

    \- May want/need to import pulpcore openapi generator utils, which
    may not be in plugin api

    Before:

    Pulp uses drf-spectacular

    A \"live\" generated version of the API is available at

    <http://localhost:5001/pulp/api/v3/docs/api.json>
    <http://localhost:5001/pulp/api/v3/docs/api.yaml>

    And a \"redoc\" view at: <http://localhost:5001/pulp/api/v3/docs/>

    Note some issues:

    -   Lots of endpoints are in the form
        \"{ansible_collection_import_href}\"
        \- in theory, all endpoints should start with a \"/\" but even
        when evaluated, the above is
        \"ansible/ansible/v3/collections/artifacts\"

    \- schema objects are inconsistent named

    :   -   pulpcore has no prefix
        -   pulp_ansible has ansible. prefix
        -   galaxy_ng sometimes? has galaxy. prefix and sometimes Galaxy

    [AAH-57](https://issues.redhat.com/browse/AAH-57)

-   Add OpenShift job template to run database migrations
    [AAH-145](https://issues.redhat.com/browse/AAH-145)

-   Allow on to customize version for sdist building
    [AAH-185](https://issues.redhat.com/browse/AAH-185)

-   Add debug level logging about access_policy permission evaluation.
    [AAH-205](https://issues.redhat.com/browse/AAH-205)

-   Add unpaginated collections, collectionversions and metadata
    endopints for better sync performance.
    [AAH-224](https://issues.redhat.com/browse/AAH-224)

-   Add rate_limit to remotes api.
    [AAH-272](https://issues.redhat.com/browse/AAH-272)

-   Add container list and detail endpoints for execution environments.
    [AAH-274](https://issues.redhat.com/browse/AAH-274)

-   Add the ability to view the changes that have been made to a
    container repo. [AAH-276](https://issues.redhat.com/browse/AAH-276)

-   Add api to return images in a container repo.
    [AAH-277](https://issues.redhat.com/browse/AAH-277)

-   Set pulp container access policies.
    [AAH-278](https://issues.redhat.com/browse/AAH-278)

-   Load initial data for repo, remote and distribution using data
    migrations [AAH-281](https://issues.redhat.com/browse/AAH-281)

-   Add GALAXY_FEATURE_FLAGS to enable/disable execution environments
    [AAH-298](https://issues.redhat.com/browse/AAH-298)

-   Add the ability to create readmes for container distributions.
    [AAH-317](https://issues.redhat.com/browse/AAH-317)

-   Add api for loading a container manifest configuration blob.
    [AAH-338](https://issues.redhat.com/browse/AAH-338)

-   Add requires_ansible to the collection api endpoints
    [AAH-409](https://issues.redhat.com/browse/AAH-409)

-   Add models for container registry sync config
    [AAH-432](https://issues.redhat.com/browse/AAH-432)

-   Allow creating super users.
    [AAH-500](https://issues.redhat.com/browse/AAH-500)

#### Bugfixes

-   Fix how travis checks for existence of Jira issues
    [AAH-44](https://issues.redhat.com/browse/AAH-44)

-   Fixed synclist curation creating 2 \* N tasks, where N is number of
    synclists. Now synclist curation is executed in batches. Number of
    batches is configured in project settings. By default it is set to
    200 synclists per task.
    [AAH-50](https://issues.redhat.com/browse/AAH-50)

-   Fix NamespaceLink creation and Validation on duplicated name.
    [AAH-132](https://issues.redhat.com/browse/AAH-132)

-   API returns 409 in case of existing group with same name.
    [AAH-152](https://issues.redhat.com/browse/AAH-152)

-   The namespaces api now performs a partial match on namespace name
    and namespace company name when using the \'keywords\' query
    parameter. [AAH-166](https://issues.redhat.com/browse/AAH-166)

-   Fix KeyError lookup in namespace and collection viewset
    [AAH-195](https://issues.redhat.com/browse/AAH-195)

-   Fix error in error msg when importing invalid filenames
    [AAH-203](https://issues.redhat.com/browse/AAH-203)

-   Fix the galaxy-importer check for max size of docs files
    [AAH-220](https://issues.redhat.com/browse/AAH-220)

-   Only show synclist toggles to org admin.

    ie, non org admin\'s should get 403 response when viewing synclist
    endpoints. [AAH-222](https://issues.redhat.com/browse/AAH-222)

-   Users should not be able to delete themselves.

    Even if they have \'delete-user\' perms.
    [AAH-265](https://issues.redhat.com/browse/AAH-265)

-   Prevent users with delete-user perms from deleting admin users
    [AAH-266](https://issues.redhat.com/browse/AAH-266)

-   Make token and password obfuscated on the API docs for /sync/config
    [AAH-282](https://issues.redhat.com/browse/AAH-282)

-   split proxy_url in 3 fields: username, password, address
    [AAH-291](https://issues.redhat.com/browse/AAH-291)

-   Fix groups endpoint viewable only by admin
    [AAH-453](https://issues.redhat.com/browse/AAH-453)

-   Expose pulp API in generated openapi spec.
    [AAH-482](https://issues.redhat.com/browse/AAH-482)

-   Replace current PULP_REDIS\* env variables with PULP_REDIS_URL env
    variable to accommodate PULP_REDIS_SSL.
    [AAH-486](https://issues.redhat.com/browse/AAH-486)

#### Misc

-   [AAH-16](https://issues.redhat.com/browse/AAH-16),
    [AAH-31](https://issues.redhat.com/browse/AAH-31),
    [AAH-120](https://issues.redhat.com/browse/AAH-120),
    [AAH-139](https://issues.redhat.com/browse/AAH-139),
    [AAH-176](https://issues.redhat.com/browse/AAH-176),
    [AAH-177](https://issues.redhat.com/browse/AAH-177),
    [AAH-257](https://issues.redhat.com/browse/AAH-257),
    [AAH-295](https://issues.redhat.com/browse/AAH-295),
    [AAH-299](https://issues.redhat.com/browse/AAH-299),
    [AAH-344](https://issues.redhat.com/browse/AAH-344),
    [AAH-387](https://issues.redhat.com/browse/AAH-387),
    [AAH-393](https://issues.redhat.com/browse/AAH-393),
    [AAH-425](https://issues.redhat.com/browse/AAH-425),
    [AAH-433](https://issues.redhat.com/browse/AAH-433),
    [AAH-478](https://issues.redhat.com/browse/AAH-478),
    [AAH-483](https://issues.redhat.com/browse/AAH-483)

------------------------------------------------------------------------

## 4.2.0 (2020-11-12)

#### Bugfixes

-   Fix URLs in remote fixtures for correct validation.
    [AAH-12](https://issues.redhat.com/browse/AAH-12)
-   Fix importer running ansible-test in local image build
    [AAH-89](https://issues.redhat.com/browse/AAH-89)
-   Fix my-synclist to show only synclists with obj permissions
    [AAH-97](https://issues.redhat.com/browse/AAH-97)

#### Misc

-   [AAH-131](https://issues.redhat.com/browse/AAH-131)

------------------------------------------------------------------------

## 4.2.0rc3 (2020-11-04)

#### Bugfixes

-   Add deprecated annotated field to empty queryset
    [AAH-122](https://issues.redhat.com/browse/AAH-122)

------------------------------------------------------------------------

## 4.2.0rc2 (2020-11-02)

#### Features

-   Support pulp_ansible collection deprecation edits
    [AAH-76](https://issues.redhat.com/browse/AAH-76)
-   Add staging and rejected repos via migration and remove from dev
    fixture [#485](https://github.com/ansible/galaxy_ng/issues/485)

#### Bugfixes

-   Update error messages on namespace links so that they can be
    differentiated from error messages on namespaces.
    [AAH-18](https://issues.redhat.com/browse/AAH-18)
-   Fix my-distributions show only sycnlist distros with obj perms
    [AAH-27](https://issues.redhat.com/browse/AAH-27)
-   Fix sort=created on ui /imports/collections/
    [AAH-98](https://issues.redhat.com/browse/AAH-98)
-   Fix [\"CollectionImport.task_id\" must be a \"CollectionImport\"
    instance.]{.title-ref} errors on import task.
    [AAH-99](https://issues.redhat.com/browse/AAH-99)

#### Misc

-   [AAH-17](https://issues.redhat.com/browse/AAH-17),
    [AAH-21](https://issues.redhat.com/browse/AAH-21),
    [AAH-26](https://issues.redhat.com/browse/AAH-26),
    [AAH-34](https://issues.redhat.com/browse/AAH-34),
    [AAH-44](https://issues.redhat.com/browse/AAH-44),
    [AAH-47](https://issues.redhat.com/browse/AAH-47),
    [AAH-81](https://issues.redhat.com/browse/AAH-81),
    [AAH-82](https://issues.redhat.com/browse/AAH-82),
    [AAH-90](https://issues.redhat.com/browse/AAH-90),
    [AAH-94](https://issues.redhat.com/browse/AAH-94),
    [AAH-105](https://issues.redhat.com/browse/AAH-105),
    [468](https://github.com/ansible/galaxy_ng/issues/468)

------------------------------------------------------------------------

## 4.2.0rc1 (2020-10-02)

#### Bugfixes

-   Make error return for upload filename parsing errors provides an
    error code \'invalid\'
    [#31](https://github.com/ansible/galaxy_ng/issues/31)
-   Fixes missing collection documentation after syncing from
    cloud.redhat.com.
    [#441](https://github.com/ansible/galaxy_ng/issues/441)
-   Add missing RepositoryVersion to inbound repos created via migration
    [#493](https://github.com/ansible/galaxy_ng/issues/493)
-   On upload use filename namespace as distro when no distro specified
    [#496](https://github.com/ansible/galaxy_ng/issues/496)

#### Misc

-   [#390](https://github.com/ansible/galaxy_ng/issues/390),
    [#473](https://github.com/ansible/galaxy_ng/issues/473)

------------------------------------------------------------------------

## 4.2.0b3 (2020-09-24)

#### Features

-   Allow a user to specify the protocol she wants to use to talk to the
    pulp backend. (ie. http vs. https)
    [#464](https://github.com/ansible/galaxy_ng/issues/464)

-   Upgrade to pulpcore 3.7.0 and allow for 3.8.0

    Based on the API stability guidance at
    <https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/concepts/index.html#plugin-api-stability-and-deprecation-policy>
    [#476](https://github.com/ansible/galaxy_ng/issues/476)

#### Misc

-   [#474](https://github.com/ansible/galaxy_ng/issues/474)

------------------------------------------------------------------------

## 4.2.0b2 (2020-09-16)

#### Features

-   The task for curating content needs to be initiated whenever a new
    collection lands in the golden repository.
    [#428](https://github.com/ansible/galaxy_ng/issues/428)

#### Bugfixes

-   Order remotes and distributions by name instead of last updated.
    [#445](https://github.com/ansible/galaxy_ng/issues/445)

#### Misc

-   [#430](https://github.com/ansible/galaxy_ng/issues/430),
    [#439](https://github.com/ansible/galaxy_ng/issues/439),
    [#449](https://github.com/ansible/galaxy_ng/issues/449),
    [#457](https://github.com/ansible/galaxy_ng/issues/457)

------------------------------------------------------------------------

## 4.2.0b1 (2020-09-11)

#### Features

-   When subscribers modify their synclist or the golden repository
    versions changes, AH needs to add/remove content from the associated
    repositories. [#17](https://github.com/ansible/galaxy_ng/issues/17)

-   Configure and manage content sync and collection remotes
    [#22](https://github.com/ansible/galaxy_ng/issues/22)

-   Support auto-created inbound pulp repositories per namespace
    [#37](https://github.com/ansible/galaxy_ng/issues/37)

-   Migration to add repo and distro for existing namespaces
    [#38](https://github.com/ansible/galaxy_ng/issues/38)

-   Add OpenAPI spec for exposing pulp collection viewsets.
    [#93](https://github.com/ansible/galaxy_ng/issues/93)

-   After successful import move collection version from incoming repo
    to staging repo
    [#117](https://github.com/ansible/galaxy_ng/issues/117)

-   Remove v3 api CollectionVersion certified flag filter
    [#120](https://github.com/ansible/galaxy_ng/issues/120)

-   Move \_ui/ to the same level as v3/ and add versions to it.
    [#225](https://github.com/ansible/galaxy_ng/issues/225)

-   Create default synclist and associated repository/distribution on
    login. [#264](https://github.com/ansible/galaxy_ng/issues/264)

-   When subscribers modify their synclist or the upstream repository
    versions changes, update the synclist repos.

    Add /curate/ endpoints to synclists (POST
    /\_ui/my-synclists/{pk}/curate/) to trigger curating a synclist
    repo.

    Add /curate/ endpoints to repositories (POST
    /content/\<repo_name\>/v3/collections/curate/ to trigger updating
    all synclists repos whose upstream_repository points to
    /content/\<repo_name\>/

    Add new tasks:

    -   curate_synclist_repository(synclist_pk)
        -   update synclist.repository based on synclist.policy,
            synclist.collections, and synclist.namespaces
    -   curate_all_synclist_repositoies(upstream_repository_name)
        -   Create a TaskGroup and create a curate_synclist_repository
            subtask for each synclist repo
        -   Also creates a GroupProgressReport for the TaskGroup
            -   Could be used to surface promotion status in UI

    Note: When using curate_all_synclist_repositoies with a lot of
    synclist repositories, it is recommended to enable multiple pulp
    workers.

    For example, if using the galaxy_ng dev docker-compose tools:

    > \$ ./compose up \--scale worker=2

    [#265](https://github.com/ansible/galaxy_ng/issues/265)

-   When creating a synclist, ensure that the curated repo and
    distribution exists, and create them if needed.
    [#267](https://github.com/ansible/galaxy_ng/issues/267)

-   Add endpoints to manage Content Sync for community and rh-certified
    repositories.
    [#282](https://github.com/ansible/galaxy_ng/issues/282)

-   API: Update org repositories when new collection version published

    For c.rh.c, when a collection version is promoted from the staging
    repository to the published repository, the subscriber org
    repositories must be updated with the new artifact.

    The promotion event has to:

    :   -   Kick-off n number of tasks, where n is the number of
            synclist repos

    [#285](https://github.com/ansible/galaxy_ng/issues/285)

-   Add endpoint to get status of pulp tasks
    [#295](https://github.com/ansible/galaxy_ng/issues/295)

-   Implement RBAC.

    -   Adds DRF Access Policy to control permissions on DRF viewsets

    \- Adds Django Guardian for assigning permissions to objects
    [#303](https://github.com/ansible/galaxy_ng/issues/303)

-   Expose the pulp core groups api. Exposes:

    -   \_ui/groups/ for listing and creating groups
    -   \_ui/groups/\<pk\> for deleting groups
    -   \_ui/groups/\<pk\>/model-permissions for listing and adding
        permissions to groups
    -   \_ui/groups/\<pk\>/model-permissions/\<pk\> for removing
        permissions from groups
    -   \_ui/groups/\<pk\>/users/ for listing and adding users to groups

    \- \_ui/groups/\<pk\>/users/\<pk\> for removing users from groups
    [#304](https://github.com/ansible/galaxy_ng/issues/304)

-   Removal of existing permission system

    -   Viewsets no longer check to see if the user is in the
        system:partner-engineers group to determine if the user is an
        admin.
    -   Red Hat entitlements checks have been moved to DRF Access Policy

    \- Existing permission classes have been removed and replaced with
    DRF Access Policy permission classes.
    [#305](https://github.com/ansible/galaxy_ng/issues/305)

-   Add relevant user permissions to the \_ui/me/ api for the UI to use.
    [#306](https://github.com/ansible/galaxy_ng/issues/306)

-   Use pulp repos to denote approved content on auto-approval
    [#316](https://github.com/ansible/galaxy_ng/issues/316)

-   Added Dockerfile.rhel8 for building docker images based on RHEL8.
    [#362](https://github.com/ansible/galaxy_ng/issues/362)

-   On publish check if inbound repo allows publishing
    [#372](https://github.com/ansible/galaxy_ng/issues/372)

-   Pin to pulpcore 3.6.0, pulp-ansible 0.2.0 and pulp-container 2.0.0
    [#380](https://github.com/ansible/galaxy_ng/issues/380)

-   Adds assign-permission management command for associating
    permissions to a group
    [#389](https://github.com/ansible/galaxy_ng/issues/389)

-   Add [distributions]{.title-ref} and [my-distributions]{.title-ref}
    endpoints to the UI api.
    [#397](https://github.com/ansible/galaxy_ng/issues/397)

#### Bugfixes

-   Fix PATCH on my-synclists
    [#269](https://github.com/ansible/galaxy_ng/issues/269)
-   Fixed bug in auto certification parameter check, that caused all
    submitted content being automatically approved.
    [#318](https://github.com/ansible/galaxy_ng/issues/318)
-   Update requirements to use latest git versions of pulp\*
    [#330](https://github.com/ansible/galaxy_ng/issues/330)
-   Update uses of pulp_ansible import_collection tasks to use
    PulpTemporaryFile
    [#333](https://github.com/ansible/galaxy_ng/issues/333)
-   chillout check_pulpcore_imports for a bit
    [#387](https://github.com/ansible/galaxy_ng/issues/387)
-   Add docs_blob to v3 api for collection versions
    [#403](https://github.com/ansible/galaxy_ng/issues/403)
-   Create namespaces on content sync
    [#404](https://github.com/ansible/galaxy_ng/issues/404)

#### Misc

-   [#297](https://github.com/ansible/galaxy_ng/issues/297),
    [#349](https://github.com/ansible/galaxy_ng/issues/349)

------------------------------------------------------------------------

## 4.2.0a10 (2020-07-15)

#### Features

-   Release packages in sdist and wheel formats. Static assets are
    download and included automatically during package build process.
    [#275](https://github.com/ansible/galaxy_ng/issues/275)

#### Misc

-   [#288](https://github.com/ansible/galaxy_ng/issues/288)

------------------------------------------------------------------------

## 4.2.0a9 (2020-07-08)

#### Features

-   Add synclist models and viewsets
    [#18](https://github.com/ansible/galaxy_ng/issues/18)
-   Add collection version move/ endpoint to move to and from repository
    [#41](https://github.com/ansible/galaxy_ng/issues/41)
-   Add synclist (blacklist/whitelist for currated sync repos) support
    [#46](https://github.com/ansible/galaxy_ng/issues/46)
-   Implement authentication API for local Automation Hub.
    [#77](https://github.com/ansible/galaxy_ng/issues/77)
-   Support config to auto-approve collection versions on import
    [#170](https://github.com/ansible/galaxy_ng/issues/170)
-   Namespace API is copied from UI to v3 and now is server at
    `<prefix>/v3/namespace/`. `<prefix>/v3/_ui/namespace/` is left as
    is. The new `<prefix>/v3/namespace/` endpoint changes how \'groups\'
    are serialized.
    [#180](https://github.com/ansible/galaxy_ng/issues/180)
-   Token API is moved from UI to v3 and now is served at
    `<prefix>/v3/auth/token/`. Token API does not support `GET` method
    anymore, token is returned to client only once after creation. Add
    support of HTTP Basic authentication method to the Token API.
    [#187](https://github.com/ansible/galaxy_ng/issues/187)
-   Enable the UI to be run as a container along with the rest of the
    development environment
    [#217](https://github.com/ansible/galaxy_ng/issues/217)
-   Fix bug preventing links from being modified on namespaces.
    [#277](https://github.com/ansible/galaxy_ng/issues/277)

#### Bugfixes

-   Fixed invalid authorization for root API endpoints
    [#108](https://github.com/ansible/galaxy_ng/issues/108)
-   Fixed galaxy-importer errors in galaxy_ng container environment
    [#110](https://github.com/ansible/galaxy_ng/issues/110)
-   Fixed collection version detail endpoint returning invalid format of
    a [collection]{.title-ref} field.
    [#113](https://github.com/ansible/galaxy_ng/issues/113)
-   Fix importer job scheduling issues with importer resource params
    [#122](https://github.com/ansible/galaxy_ng/issues/122)
-   Fix importer exception on unexpected docstring format
    [#159](https://github.com/ansible/galaxy_ng/issues/159)
-   Fix CollectionVersionViewSet so it filters based on
    \"certification\" status.
    [#214](https://github.com/ansible/galaxy_ng/issues/214)
-   Fix compose file name mismatch. In fixture data associate admin user
    with system:partner-engineers group.
    [#233](https://github.com/ansible/galaxy_ng/issues/233)
-   Fix wrong href\'s in results from collection viewsets
    [#247](https://github.com/ansible/galaxy_ng/issues/247)
-   Add back workaround for multipart forms from ansible-galaxy.
    [#256](https://github.com/ansible/galaxy_ng/issues/256)

#### Misc

-   [#118](https://github.com/ansible/galaxy_ng/issues/118),
    [#130](https://github.com/ansible/galaxy_ng/issues/130),
    [#131](https://github.com/ansible/galaxy_ng/issues/131),
    [#205](https://github.com/ansible/galaxy_ng/issues/205),
    [#209](https://github.com/ansible/galaxy_ng/issues/209),
    [#276](https://github.com/ansible/galaxy_ng/issues/276)

------------------------------------------------------------------------
