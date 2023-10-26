import semantic_version
from ansible.module_utils.compat.version import LooseVersion


def parse_version_tag(value):
    value = str(value)
    if not value:
        raise ValueError('Empty version value')
    if value[0].lower() == 'v':
        value = value[1:]
    return semantic_version.Version(value)


def sort_versions(versions):
    """
    Use ansible-core's LooseVersion util to sort the version dicts by the tag key.
    """

    def get_version_tag(version):
        """
        Necessary until we normalize all versions.
        """
        if version.get('version'):
            return version['version']
        elif version.get('tag'):
            return version['tag']
        elif version.get('name'):
            return version['name']
        return ''

    try:
        sorted_versions = sorted(
            versions,
            key=lambda x: LooseVersion(
                get_version_tag(x).lower()
            )
        )
    except TypeError:
        # we did our best, it'll have to be unsorted.
        return versions
    except AttributeError:
        # we did our best, it'll have to be unsorted.
        return versions

    return sorted_versions
