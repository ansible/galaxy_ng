All collections to be importer to any repo, not just inbound-namespace


Notes:

My proposal is based on the idea of being able to push any content to a repo
/dist  (ie, POST api/automation-hub/content/<str:path>/v3/collections/).


A Post there is implemented via
galaxy_ng.app.api.v3.viewsets.collections.CollectionUploadViewSet.create()
Currently, it has some logic to figure out the inbound repo based on the
artifact filename and matching that to a namespace that corresponds (as exists
in c.r.c).


But for standalone, a POST to
/api/automation-hub/content/mycustomrepo/v3/collections/  would enqueue an
import to 'inbound-mycustomrepo'.

Depending on config for 'autopromote' it may automatically get moved to
mycustomrepo if import succeeds, or it may move to a staging repo.


This allows customers to push arbitrary collections with no regard to
namespaces into repositories that they control.

It also eliminates the need for creating inbound-<namespace> repos for every
namespace.

Most of this would be done in  CollectionUploadViewSet.create() and could be
enable/disabled based on deployment mode.


This also allows customers to use the ansible-galaxy config that is provided on
the 'Repo Management' page
(http://localhost:8002/ui/repositories?page_size=10&tab=local).

They would only need to configure one repo or /content/<name>/ endpoint, and it
would be used for both download and publishing content.

Under the covers content published to
/api/automation-hub/content/mycustomrepo/v3/collections/  gets directed to the
matching inbound repo.
