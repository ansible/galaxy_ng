import logging
import os
import tempfile
import subprocess
from urllib.parse import urljoin

from django.conf import settings
from galaxy_ng.app.auth.auth import TaskAuthentication

log = logging.getLogger(__name__)


def build_task(
    execution_environment_yaml,
    container_name,
    container_tag,
    username
):
    """Build EE image with ansible-builder."""

    tdir = tempfile.mkdtemp(prefix='ansible-builder-', dir='/tmp')

    if not os.path.exists(tdir):
        os.makedirs(tdir)

    ee_path = os.path.join(tdir, "execution-environment.yml")
    with open(ee_path, 'w') as f:
        f.write(execution_environment_yaml)

    container_registry = os.environ.get("CONTAINER_REGISTRY", "localhost:5001")
    ssl_verify = os.environ.get("SSL_VERIFY", False)

    tag = f"{container_registry}/{container_name}:{container_tag}"

    token = TaskAuthentication().get_token(username)

    url = urljoin(settings.ANSIBLE_API_HOSTNAME, settings.GALAXY_API_PATH_PREFIX)

    log.info(f"Adding ansible.cfg to {tdir}")
    cfgfile = os.path.join(tdir, 'ansible.cfg')
    with open(cfgfile, 'w') as f:
        f.write('[galaxy]\n')
        f.write('server_list = automation_hub\n')
        f.write('\n')
        f.write('[galaxy_server.automation_hub]\n')
        f.write(f'url={url}\n')
        f.write(f'token={token}\n')

    log.info(f"Running ansible-builder build --tag={tag}")
    process = subprocess.run(
        [
            "ansible-builder", "build", f"--tag={tag}"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tdir
    )

    if process.returncode != 0:
        raise RuntimeError(str(process.stdout))

    log.info(f"Running podman push {tag}")
    process = subprocess.run(
        [
            "podman", "push", tag,
            "--creds", f"{username}:{token}",
            f"--tls-verify={ssl_verify}"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tdir
    )

    if process.returncode != 0:
        raise RuntimeError(str(process.stdout))
