#!/usr/bin/env python3

"""
dependency_bumper.py - bumps dependencies in ALL the branches at the same time

usage:
    1) export GITHUB_USER=<your-github-username>
    2) python3 dependency_bumper.py

options kwargs:
    --workdir ... tells the script where to do all of the work
    --branch ... just operate on a single branch by name
    --file ... just operate on a single requirements file [I don't know why you would do this]
    --package ... update a single package [django won't autoupdate if you update pulp*]
    --nothreads ... run slower but with easier to read output

notes:
    - the default behavior is to bump all dependencies in all branches
    - each python, pip and pip-tools version were pinned based on the results
    - older versions of pip-tools were used to make the requirements in 4.2
      and the format is similar to the --annotation-style=line argument
      introduced in v6.

maintenance:
    - if a new stable branch is created, it should be added to the MATRIX variable
"""

import argparse
import datetime
import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
from typing import Optional
from threading import Thread


MATRIX = [
    {
        'branch': 'stable-4.2',
        'python': '3.9',
        'pip': '22.1.2',
        'pip_tools': '6.6.2',
    },
    {
        'branch': 'stable-4.3',
        'python': '3.9',
        'pip': '22.1.2',
        'pip_tools': '6.6.2',
    },
    {
        'branch': 'stable-4.4',
        'python': '3.9',
        'pip': '22.1.2',
        'pip_tools': '6.6.2',
    },
    {
        'branch': 'stable-4.5',
        'python': '3.9',
        'pip': '22.1.2',
        'pip_tools': '6.6.2',
    },
    {
        'branch': 'main',
        'python': '3.9',
        'pip': '22.1.2',
        'pip_tools': '6.6.2',
    },

]

if 'GITHUB_USER' not in os.environ:
    raise Exception('GITHUB_USER must be set as an environment variable')
GITHUB_USER = os.environ['GITHUB_USER']
REPO = f"git@github.com:{GITHUB_USER}/galaxy_ng"
UPSTREAM = "https://github.com/ansible/galaxy_ng"

BASE_IMAGE = 'python:3.8'  # includes 3.9
IMAGE = 'pipcompiler:latest'

REQUIREMENTS_FILES = [
    ['requirements/requirements.txt'],
    ['requirements/requirements.common.txt'],
    ['requirements/requirements.insights.txt', 'requirements/requirements.insights.in'],
    ['requirements/requirements.standalone.txt', 'requirements/requirements.standalone.in']
]


def threaded_command(cmd: str) -> subprocess.CompletedProcess:
    """
    threaded_command runs a stringified command with subprocess and returns the result

    :param cmd: a stringified shell command
    :return: a completed process result
    """
    return subprocess.run(cmd, shell=True)


def make_image() -> None:
    """
    make_image builds the image necesary to run pip-compile in various ways

    :return: None
    """

    tdir = tempfile.mkdtemp(prefix='pipcompile-docker-')
    fname = os.path.join(tdir, 'Dockerfile')
    with open(fname, 'w') as f:
        f.write(f'FROM {BASE_IMAGE}\n')
        f.write('RUN apt -y update\n')
        f.write('RUN apt -y install python3-virtualenv python3-venv python3-pip\n')
        f.write('RUN python3.8 -m venv /venv-3.8\n')
        f.write('RUN python3.9 -m venv /venv-3.9\n')
        f.write('RUN /venv-3.8/bin/pip install --upgrade pip wheel\n')
        f.write('RUN /venv-3.9/bin/pip install --upgrade pip wheel\n')

    pid = subprocess.run(f'docker build -t {IMAGE} .', shell=True, cwd=tdir)
    assert pid.returncode == 0

    shutil.rmtree(tdir)


def construct_checkout(
    checkout: str,
    base_branch: Optional[str] = None,
    new_branch: Optional[str] = None,
) -> None:
    """
    construct_checkout makes a ready-to-go clone and branch of $REPO

    :param checkout: the filepath where the clone is created
    :param base_branch: after pull and rebase, checkout this branch
    :param new_branch: checkout a new branch by this name
    :return: None
    """

    # make the checkout
    pid = subprocess.run(f'git clone {REPO} {checkout}', shell=True)
    assert pid.returncode == 0

    # add upstream
    pid = subprocess.run(f'git remote add upstream {UPSTREAM}', shell=True, cwd=checkout)
    assert pid.returncode == 0

    # fetch
    pid = subprocess.run('git fetch -a && git fetch upstream', shell=True, cwd=checkout)
    assert pid.returncode == 0

    # rebase
    pid = subprocess.run('git pull --rebase upstream main', shell=True, cwd=checkout)
    assert pid.returncode == 0

    # set the starting branch
    if base_branch:
        pid = subprocess.run(f'git checkout upstream/{base_branch}', shell=True, cwd=checkout)
        assert pid.returncode == 0

    # create a new branch
    if new_branch:
        pid = subprocess.run(f'git checkout -b {new_branch}', shell=True, cwd=checkout)
        assert pid.returncode == 0


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--branch', action='append', help="limit to this branch name")
    parser.add_argument('--file', action='append', help="limit to this requirements filename")
    parser.add_argument('--package', action='append', help="limit to this package name")
    parser.add_argument('--nothreads', action='store_true', help="run single threaded")
    parser.add_argument('--workdir', help="store results here [random tmpdir by default]")
    args = parser.parse_args()

    make_image()

    workdir = args.workdir or tempfile.mkdtemp(prefix='galaxy-django-bump-')
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    # these commands will be threaded
    container_commands = []

    for cfg in MATRIX:

        # prefer dot notation in string formatting ...
        cfg = SimpleNamespace(**cfg)

        # skip unselected branches
        if args.branch and cfg.branch not in args.branch:
            continue

        # make a unique checkout for this new patch
        branch_checkout = os.path.join(workdir, f'galaxy_ng.{cfg.branch}')
        ts = datetime.datetime.now().strftime("%Y_%m_%dT%H_%M_%S")  # noqa: DTZ005
        new_branch = f'BUMP_DEPS_{ts}_{cfg.branch}'.replace('-', '_').replace('.', '_')
        construct_checkout(branch_checkout, base_branch=cfg.branch, new_branch=new_branch)

        # assemble the container internal script
        commands = [
            f'source /venv-{cfg.python}/bin/activate',
            f'/venv-{cfg.python}/bin/pip install --upgrade pip=={cfg.pip}',
            f'/venv-{cfg.python}/bin/pip install pip-tools=={cfg.pip_tools}',
        ]

        # be smarter than the makefile
        for RF in REQUIREMENTS_FILES:
            if args.file and RF not in args.file:
                continue
            if os.path.exists(os.path.join(branch_checkout, RF[0])):
                filecmd = 'PYTHONPATH=.'
                filecmd += f' /venv-{cfg.python}/bin/pip-compile -o {" ".join(RF)} setup.py'
                if args.package:
                    for ap in args.package:
                        filecmd += f' --upgrade-package {ap}'
                commands.append(filecmd)

        script = ' && '.join(commands)
        cname = f'bumper_{cfg.branch}'
        cmd = f'docker run --name="{cname}"'
        cmd += f' -v {branch_checkout}:/app -w /app -it {IMAGE} /bin/bash -c "{script}"'
        container_commands.append(cmd)

    if args.nothreads:
        # run each command serially
        for cc in container_commands:
            pid = subprocess.run(cc, shell=True)
            assert pid.returncode == 0
    else:
        # thread all the commands
        threads = []
        for cc in container_commands:
            threads.append(Thread(target=threaded_command, args=(cc,)))
        for thread in threads:
            thread.start()
        results = []
        for thread in threads:
            results.append(thread.join())

    print(f'pip-compile completed, make PRs from the subdirectories in {workdir}')


if __name__ == "__main__":
    main()
