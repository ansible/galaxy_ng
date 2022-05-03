"""test_package.py - Tests related to setup.py

See: https://issues.redhat.com/browse/AAH-1545

"""

import pytest
import subprocess
import tempfile


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.standalone_only
@pytest.mark.package
@pytest.mark.parametrize(
    "env_vars",
    [
        {},
        {'LOCK_REQUIREMENTS': '0'}
    ]
)
def test_package_install(env_vars):
    """smoktest setup.py"""

    with tempfile.TemporaryDirectory(prefix='galaxy_ng_testing_') as basedir:

        # make a venv
        pid = subprocess.run(f'python3 -m venv {basedir}/venv', shell=True)
        assert pid.returncode == 0

        # install the package
        cmd = f'{basedir}/venv/bin/pip install .'
        if env_vars:
            for k, v in env_vars.items():
                cmd = f'{k}={v} {cmd}'
        pid = subprocess.run(cmd, shell=True)
        assert pid.returncode == 0

        # check the installed packages
        cmd = f'{basedir}/venv/bin/pip list'
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        assert pid.returncode == 0

        package_list = pid.stdout.decode('utf-8')
        package_list = package_list.split('\n')
        package_list = [x.strip() for x in package_list if x.strip()]
        package_list = [x for x in package_list if not x.startswith('Package')]
        package_list = [x for x in package_list if not x.startswith('-')]
        package_names = [x.split()[0] for x in package_list]

        assert 'pulpcore' in package_names
        assert 'pulp-ansible' in package_names
        assert 'pulp-container' in package_names
        assert 'galaxy-ng' in package_names
