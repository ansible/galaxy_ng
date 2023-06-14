import pytest

import subprocess


def run_api_container_command(cmd):
    cmd = f'./compose exec api /bin/bash -c "{cmd}"'
    pid = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return pid.returncode, pid.stdout.decode('utf-8')


@pytest.mark.community_only
def test_analytics_export_local_command(auto_approved_artifacts):
    """
    Validate the analytics export with the local version so that
    we don't need real or mocked S3 to check it's basic function.
    """

    # run the export command ...
    export_rc, export_log = run_api_container_command('pulpcore-manager analytics-export-local')
    assert export_rc == 0

    # extract tarball filepath from the output ...
    lines = export_log.split('\n')
    tarfile = [x for x in lines if 'data has been saved to:' in x][0]
    tarfile = tarfile.split()[-1]

    # verify it exists ...
    exists_rc, exists_output = run_api_container_command(f'test -f {tarfile} && echo \"exists\"')
    assert exists_rc == 0

    # verify it has some content ...
    listing_rc, listing_output = run_api_container_command(f'tar tzvf {tarfile}')
    assert listing_rc == 0
    content = listing_output.split('\n')
    content = [x for x in content if x.startswith('-r')]
