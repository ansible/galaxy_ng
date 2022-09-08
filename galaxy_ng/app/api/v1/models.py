from django.db import models

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import User


"""
The core cli accepts a single string argument for the role as user would like to install.
The string is parsed by a RoleRequirement class into a dictionary of parts.

    from ansible.playbook.role.requirement import RoleRequirement
        AnsibleError("Invalid role line (%s). Proper format is 'role_name[,version[,name]]'" % role)

If no commas are in the string, it becomes the name and the src ...

    RoleRequirement.role_yaml_parse('zyun_i.ansible_role_wireguard')
    {
        'name': 'zyun_i.ansible_role_wireguard',
        'src': 'zyun_i.ansible_role_wireguard',
        'scm': None,
        'version': None
    }

If a single comma, the first segment becomes the name+src and the second becomse the version.

    RoleRequirement.role_yaml_parse('zyun_i.ansible_role_wireguard,master')
    {
        'name': 'zyun_i.ansible_role_wireguard',
        'src': 'zyun_i.ansible_role_wireguard',
        'scm': None,
        'version': 'master'
    }

If two commas, the third segment is the name. This is primarily used when
the first segment is a url which can be git cloned.

    RoleRequirement.role_yaml_parse('zyun_i.ansible_role_wireguard,master,foo')
    {
        'name': 'foo',
        'src': 'zyun_i.ansible_role_wireguard',
        'scm': None,
        'version': 'master'
    }

The above information is important to understand when examining how the cli
determines what the role version is and how to obtain it.

If an scm is given, the cli clones the repo to a temp dir and continues
processing from there.

If src is set, which is usually <user>.<name> in most cases, and the version
is not set, then the code uses an algorithm to figure out the version.

    * get the role data from v1/roles/ by searching
        owner__username=<user>&name=<name>
    * retrieve the list of versions via v1/roles/<roleid>
    * if the role has versions, use the newest according to LooseVersion
    * if no versions, use the github_branch
    * if no branch, use "master"

Finally the code will assemble an archive url and fetch that and extact
it to a temp dir for further processing.

    https://github.com/{user}/{name}/archive/{version}.tar.gz

The key point from all of this is that many roles do not have a true "version".
"""


class LegacyNamespace(models.Model):
    """
    A legacy namespace, aka a github username.

    Namespaces in the galaxy_ng sense are very restrictive
    with their character sets. This is primarily due to how
    collection namespaces and names must be pythonic and
    importable module names. Legacy roles had no such
    restrictions and were 1:1 with whatever github allowed
    for a username.

    This model exists for a few reasons:
        1) enable an endpoint for v1/users with no sql hacks
        2) enable the ui to list namespaces with avatar icons
        3) to map the legacy namespace to a new namespace
           which can have galaxy_ng style permission management
        4) to define what users aside from the creator can
           "own" the roles under the namespace.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=64, unique=True, blank=False)
    company = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=256, blank=True)
    avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)

    namespace = models.ForeignKey(
        Namespace,
        null=True,
        on_delete=models.SET_NULL,
        related_name="namespace",
    )

    owners = models.ManyToManyField(
        User,
        editable=True
    )


class LegacyRole(models.Model):
    """
    A legacy v1 role, which is just an index for github.

    These are not "content" in the pulp sense. They are simply
    an index of repositories on github.com that have the shape
    of a standalone role. Nothing is stored on disk or served
    out to the client from the server besides json metadata.

    Sometimes they have versions and sometimes not, hence
    there is no LegacyRoleVersion model.

    Rather than make many many fields and many many models
    to encapsulate the various type of data for a role, this model
    uses a json field to store everything. It is effectively
    mimic'ig a NOSQL database in that regard. Instead of
    adding new fields here as requirements change, store the new
    data in the full_metadata field and alter the serializer
    to expose that new data or to munge old data. For example,
    the docs_blob is a key inside full_metadata.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    namespace = models.ForeignKey(
        'LegacyNamespace',
        related_name='roles',
        editable=False,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=64, unique=False, blank=False)

    full_metadata = models.JSONField(
        null=False,
        default=dict
    )
