import subprocess
import warnings

TAG_PREFIX = 'v'


def get_git_version():
    """
    Returns package version in PEP440 format based on latest annotated
    version tag. Version tags should have prefix 'v'.
    :return str: A version string.
    :raises RuntimeError: If cannot determine git version string.
    """
    try:
        # TODO(cutwater): Replace `.decode('utf-8')` call with subprocess
        # parameter `encoding` after dropping Python 2.7 support.
        tag_info = subprocess.check_output([
            'git', 'describe', '--always', '--match', TAG_PREFIX + '*']
        ).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        warnings.warn('Cannot determine git version string.')
        return '0.0.0'

    if '-' in tag_info:
        chunks = tag_info.lstrip(TAG_PREFIX).rsplit('-', 2)
        return '{0}.dev{1}+{2}'.format(*chunks)

    if '.' in tag_info:
        return tag_info.lstrip(TAG_PREFIX)

    return '0.0.0.dev0+{0}'.format(tag_info)
