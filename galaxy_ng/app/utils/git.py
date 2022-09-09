import subprocess
import tempfile


def get_tag_commit_date(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        pid = subprocess.run(f'git clone {git_url} {checkout_path}', shell=True)
    pid = subprocess.run(
        "git log -1 --format='%ci'",
        shell=True,
        cwd=checkout_path,
        stdout=subprocess.PIPE
    )
    commit_date = pid.stdout.decode('utf-8').strip()

    # 2022-06-07 22:18:41 +0000 --> 2022-06-07T22:18:41
    parts = commit_date.split()
    ts = f"{parts[0]}T{parts[1]}"
    return ts


def get_tag_commit_hash(git_url, tag, checkout_path=None):
    if checkout_path is None:
        checkout_path = tempfile.mkdtemp()
        pid = subprocess.run(f'git clone {git_url} {checkout_path}', shell=True)
    pid = subprocess.run(
        "git log -1 --format='%H'",
        shell=True,
        cwd=checkout_path,
        stdout=subprocess.PIPE
    )
    commit_hash = pid.stdout.decode('utf-8').strip()
    return commit_hash
