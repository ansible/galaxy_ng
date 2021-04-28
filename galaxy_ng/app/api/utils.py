from collections import namedtuple
import re

from galaxy_importer.schema import MAX_LENGTH_NAME, MAX_LENGTH_VERSION

CollectionFilename = namedtuple("CollectionFilename", ["namespace", "name", "version"])

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
        msg = "Invalid filename {filename}. Expected format: namespace-name-version.tar.gz"
        raise ValueError(msg.format(filename=filename))

    namespace, name, version = match.groups()

    match = VERSION_REGEXP.match(version)
    if not match:
        msg = "Invalid version string {version} from filename {filename}. Expected semantic version format." # noqa
        raise ValueError(msg.format(version=version, filename=filename))

    if len(namespace) > MAX_LENGTH_NAME:
        raise ValueError(f"Expected namespace to be max length of {MAX_LENGTH_NAME}")
    if len(name) > MAX_LENGTH_NAME:
        raise ValueError(f"Expected name to be max length of {MAX_LENGTH_NAME}")
    if len(version) > MAX_LENGTH_VERSION:
        raise ValueError(f"Expected version to be max length of {MAX_LENGTH_VERSION}")

    return CollectionFilename(namespace, name, version)
