import re
import socket

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from pulpcore.plugin import models as pulp_models

from collections import namedtuple
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.connectionpool import HTTPConnectionPool

from galaxy_importer.schema import MAX_LENGTH_NAME, MAX_LENGTH_VERSION

CollectionFilename = namedtuple("CollectionFilename", ["namespace", "name", "version"])

LOCALHOST = "localhost"
FILENAME_REGEXP = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-" r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)
VERSION_REGEXP = re.compile(r"""
^
(?P<major>0|[1-9][0-9]*)
\.
(?P<minor>0|[1-9][0-9]*)
\.
(?P<patch>0|[1-9][0-9]*)
(?:
    -(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)
)?
(?:
    \+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)
)?
$
""", re.VERBOSE | re.ASCII)


def parse_collection_filename(filename):
    """
    Parses collection filename.

    Parses and validates collection filename. Returns CollectionFilename named tuple.
    Raises ValueError if filename is not a valid collection filename.
    """
    match = FILENAME_REGEXP.match(filename)

    if not match:
        msg = _("Invalid filename {filename}. Expected format: namespace-name-version.tar.gz")
        raise ValueError(msg.format(filename=filename))

    namespace, name, version = match.groups()

    match = VERSION_REGEXP.match(version)
    if not match:
        msg = _("Invalid version string {version} from filename {filename}. Expected semantic version format.") # noqa
        raise ValueError(msg.format(version=version, filename=filename))

    if len(namespace) > MAX_LENGTH_NAME:
        raise ValueError(_("Expected namespace to be max length of %s") % MAX_LENGTH_NAME)
    if len(name) > MAX_LENGTH_NAME:
        raise ValueError(_("Expected name to be max length of %s") % MAX_LENGTH_NAME)
    if len(version) > MAX_LENGTH_VERSION:
        raise ValueError(_("Expected version to be max length of %s") % MAX_LENGTH_VERSION)

    return CollectionFilename(namespace, name, version)


class SocketHTTPConnection(HTTPConnection):
    def __init__(self, socket_file):
        self.socket_file = socket_file
        super().__init__(LOCALHOST)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_file)


class SocketHTTPConnectionPool(HTTPConnectionPool):
    def __init__(self, socket_file):
        self.socket_file = socket_file
        super().__init__(LOCALHOST)

    def _new_conn(self):
        return SocketHTTPConnection(self.socket_file)


class SocketHTTPAdapter(HTTPAdapter):
    def __init__(self, socket_file):
        self.socket_file = socket_file
        super().__init__()

    def get_connection(self, url, proxies=None):
        return SocketHTTPConnectionPool(self.socket_file)


def get_write_only_fields(serializer, obj, extra_data=None):
    """
    Returns a list of write only fields and whether or not their values are set
    so that clients can tell if they are overwriting an existing value.
    serializer: Serializer instance
    obj: model object being serialized
    extra_data: extra fields that might not be on obj. This is used when a write
        only field is not one of the fields in the underlying data model.
    """
    fields = []
    extra_data = extra_data or {}

    # returns false if field is "" or None
    def _is_set(field_name):
        if (field_name in extra_data):
            return bool(extra_data[field_name])
        else:
            return bool(getattr(obj, field_name))

    # There are two ways to set write_only. This checks both.

    # check for values that are set to write_only in Meta.extra_kwargs
    for field_name in serializer.Meta.extra_kwargs:
        if serializer.Meta.extra_kwargs[field_name].get('write_only', False):
            fields.append({"name": field_name, "is_set": _is_set(field_name)})

    # check for values that are set to write_only in fields
    serializer_fields = serializer.get_fields()
    for field_name in serializer_fields:
        if (serializer_fields[field_name].write_only):
            fields.append({"name": field_name, "is_set": _is_set(field_name)})

    return fields


class RemoteSyncTaskField(serializers.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, read_only=True)

    def to_representation(self, remote):
        # Query the database for sync tasks that reserve the given remote's PK
        task = pulp_models.Task.objects.filter(
            reserved_resources_record__icontains=remote.pk,
            name__icontains="sync"
        ).order_by('-pulp_last_updated').first()

        if not task:
            return {}
        else:
            return {
                "task_id": task.pk,
                "state": task.state,
                "started_at": task.started_at,
                "finished_at": task.finished_at,
                "error": task.error
            }
