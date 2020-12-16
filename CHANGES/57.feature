Enable OpenAPI spec at cloud.redhat.com/api/automation-hub/v3/openapi.json

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
