#!/usr/bin/env python
"""
Usage:
    generate_python_manifest.py [-h] [-r REQUIREMENTS] [-o OUTPUT]
"""

import sys
import argparse

from pip._internal.network.session import PipSession
from pip._internal.req import parse_requirements


PREFIX = 'services-ansible-automation-hub:api'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-r',
        '--requirements',
        default='requirements.txt',
    )
    parser.add_argument(
        '-o',
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout,
    )

    return parser.parse_args()


def process_requirements(requirements):
    for req in requirements:
        if req.requirement.startswith('git+'):
            continue
        package, version = req.requirement.split('==')
        yield '{prefix}/{package}:{version}.pypi'.format(
            prefix=PREFIX,
            package=package,
            version=version,
        )


def main():
    args = parse_args()

    requirements = parse_requirements(args.requirements, session=PipSession())
    for record in sorted(process_requirements(requirements)):
        args.output.write(record + '\n')


if __name__ == '__main__':
    main()
