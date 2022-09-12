import logging
import os
import re
import shutil
import tempfile
import time

from subprocess import run, PIPE

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_POLLING


logger = logging.getLogger(__name__)


def ansible_galaxy(
    command,
    retries=3,
    check_retcode=0,
    server="automation_hub",
    ansible_config=None,
    token=None,
    force_token=False,
    cleanup=True
):

    # Allow kwargs to override token auth
    if token is None and ansible_config.get('token'):
        token = ansible_config.get('token')

    tdir = tempfile.mkdtemp(prefix='ansible-galaxy-testing-')
    if not os.path.exists(tdir):
        os.makedirs(tdir)
    cfgfile = os.path.join(tdir, 'ansible.cfg')
    with open(cfgfile, 'w') as f:
        f.write('[galaxy]\n')
        f.write(f'server_list = {server}\n')
        f.write('\n')
        f.write(f'[galaxy_server.{server}]\n')
        f.write(f"url={ansible_config.get('url')}\n")
        if ansible_config.get('auth_url'):
            f.write(f"auth_url={ansible_config.get('auth_url')}\n")
        f.write('validate_certs=False\n')
        if not force_token:
            f.write(f"username={ansible_config.get('username')}\n")
            f.write(f"password={ansible_config.get('password')}\n")
        if token:
            f.write(f"token={token}\n")

    command_string = f"ansible-galaxy -vvv {command} --server={server} --ignore-certs"

    for x in range(0, retries + 1):
        try:
            p = run(command_string, cwd=tdir, shell=True, stdout=PIPE, stderr=PIPE, env=os.environ)
            logger.debug(f"RUN [retry #{x}] {command_string}")
            logger.debug("STDOUT---")
            for line in p.stdout.decode("utf8").split("\n"):
                logger.debug(re.sub("(.\x08)+", "...", line))
            logger.debug("STDERR---")
            for line in p.stderr.decode("utf8").split("\n"):
                logger.debug(re.sub("(.\x08)+", "...", line))
            if p.returncode == 0:
                break
            if p.returncode != 0 and not check_retcode:
                break
        except Exception as e:
            logger.exception(e)
            time.sleep(SLEEP_SECONDS_POLLING)

    if check_retcode is not False:
        assert p.returncode == check_retcode, p.stderr.decode("utf8")
    if cleanup:
        shutil.rmtree(tdir)
    return p
