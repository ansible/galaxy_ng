import re
from galaxy_importer.constants import NAME_REGEXP


def generate_v3_namespace_from_attributes(username=None, github_id=None):

    if validate_namespace_name(username):
        return username

    transformed = transform_namespace_name(username)
    if validate_namespace_name(transformed):
        return transformed

    return map_v3_namespace(username)


def map_v3_namespace(v1_namespace):
    """
    1. remove unwanted characters
    2. convert - to _
    3. if name starts with number or _, prepend prefix
    """

    prefix = "gh_"
    no_start = tuple(x for x in "0123456789_")

    name = v1_namespace.lower()
    name = name.replace("-", "_")
    name = re.sub(r'[^a-z0-9_]', "", name)
    if name.startswith(no_start) or len(name) <= 2:
        name = prefix + name.lstrip("_")

    return name


def generate_available_namespace_name(Namespace, login, github_id):
    # we're only here because session_login is already taken as
    # a namespace name and we need a new one for the user

    # this makes the weird gh_{BLAH} name ...
    # namespace_name = ns_utils.map_v3_namespace(session_login)

    # we should iterate and append 0,1,2,3,4,5,etc on the login name until we find one that is free
    counter = -1
    while True:
        counter += 1
        namespace_name = transform_namespace_name(login) + str(counter)
        if Namespace.objects.filter(name=namespace_name).count() == 0:
            return namespace_name


def validate_namespace_name(name):
    """Similar validation to the v3 namespace serializer."""

    # galaxy has "extra" requirements for a namespace ...
    # https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/constants.py#L45
    # NAME_REGEXP = re.compile(r"^(?!.*__)[a-z]+[0-9a-z_]*$")

    if not NAME_REGEXP.match(name):
        return False
    if len(name) < 2:
        return False
    if name.startswith('_'):
        return False
    return True


def transform_namespace_name(name):
    """Convert namespace name to valid v3 name."""
    return name.replace('-', '_').lower()
