import logging
import os
import tempfile
import subprocess

from galaxy_ng.app.auth.auth import TaskAuthenticationClass


log = logging.getLogger(__name__)


def build_image_task(
    execution_environment_yaml,
    container_name,
    container_tag,
    username
):
    """Build EE image with ansible-builder."""

    tdir = tempfile.mkdtemp(prefix='ansible-builder-', dir='/tmp')

    if not os.path.exists(tdir):
        os.makedirs(tdir)

    def_file = os.path.join(tdir, "execution-environment.yml")
    with open(def_file, 'w') as f:
        f.write(execution_environment_yaml)

    container_registry = os.environ.get("CONTAINER_REGISTRY", "localhost:5001")
    ssl_verify = os.environ.get("SSL_VERIFY", False)

    tag = f"{container_registry}/{container_name}:{container_tag}"

    token = TaskAuthenticationClass().get_token(username)

    log.info(f"Adding ansible.cfg to {tdir}")
    cfgfile = os.path.join(tdir, 'ansible.cfg')
    with open(cfgfile, 'w') as f:
        f.write('[galaxy]\n')
        f.write('server_list = automation_hub\n')
        f.write('\n')
        f.write('[galaxy_server.automation_hub]\n')
        f.write('url=http://localhost:5001/api/galaxy/\n')
        f.write(f'token={token}\n')

    log.info(f"Running ansible-builder build --tag={tag}")
    subprocess.run(
        [
            "ansible-builder", "build", f"--tag={tag}"
            # "--build-arg", f"ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN='{token}'"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tdir
    )

    log.info(f"Running podman push {tag}")
    subprocess.run(
        [
            "podman", "push", tag,
            "--creds", f"{username}:{token}",
            f"--tls-verify={ssl_verify}"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tdir
    )
