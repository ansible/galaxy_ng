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

4.2.0a11 (2020-07-24)
=====================

Bugfixes
--------

- Fixed bug in auto certification parameter check, that caused all submitted content being automatically approved.
  `#318 <https://github.com/ansible/galaxy_ng/issues/318>`_


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


