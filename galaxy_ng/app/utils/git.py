import subprocess
import tempfile

_CLONE_TIMEOUT = 300
_GIT_CMD_TIMEOUT = 60


def get_tag_commit_date(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        subprocess.run(
            ['git', 'clone', '--', git_url, checkout_path],
            capture_output=True,
            check=True,
            timeout=_CLONE_TIMEOUT,
        )
    pid = subprocess.run(
        ['git', 'log', '-1', '--format=%ci'],
        cwd=checkout_path,
        capture_output=True,
        check=True,
        timeout=_GIT_CMD_TIMEOUT,
    )
    commit_date = pid.stdout.decode('utf-8').strip()

    # 2022-06-07 22:18:41 +0000 --> 2022-06-07T22:18:41
    parts = commit_date.split()
    ts = f"{parts[0]}T{parts[1]}"
    return ts


def get_tag_commit_hash(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        subprocess.run(
            ['git', 'clone', '--', git_url, checkout_path],
            capture_output=True,
            check=True,
            timeout=_CLONE_TIMEOUT,
        )
    proc = subprocess.run(
        ['git', 'log', '-1', '--format=%H'],
        cwd=checkout_path,
        capture_output=True,
        check=True,
        timeout=_GIT_CMD_TIMEOUT,
    )
    commit_hash = proc.stdout.decode('utf-8').strip()
    return commit_hash
