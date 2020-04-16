#!/usr/bin/env python3

from setuptools import find_packages, setup

# NOTE(cutwater): Because bindings are statically generated, requirements list
#   from pulp-galaxy/setup.py has to be copied here and manually maintained.
galaxy_pulp_requirements = [
    "urllib3 >= 1.15",
    "six >= 1.10",
    "certifi",
    "python-dateutil"
]

requirements = galaxy_pulp_requirements + [
    "Django~=2.2.3",
    "pulpcore>=3.0,<3.3",
    "pulp-ansible>=0.2.0b11",
    "django-prometheus>=2.0.0",
    "django-storages[boto3]",
]


setup(
    name="galaxy-ng",
    version="0.1.0a1",
    description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="AUTHOR",
    author_email="author@email.here",
    url="http://example.com/",
    python_requires=">=3.6",
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=(
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ),
    entry_points={"pulpcore.plugin": ["galaxy_ng = galaxy_ng:default_app_config"]},
)
