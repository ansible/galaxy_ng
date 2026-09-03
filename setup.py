#!/usr/bin/env python3

import os

from setuptools import find_packages, setup

package_name = os.environ.get("GALAXY_NG_ALTERNATE_NAME", "galaxy-ng")
version = "4.12.0dev"

requirements = [
    "galaxy-importer>=0.4.31,<0.5.0",
    "pulpcore>=3.105.17,<3.106",
    "pulp_ansible>=0.30.0,<0.31",
    "pulp-container>=2.27.11,<2.28",
    "pyjwt[crypto]>=2.13.0",  # minimum version enforced to address AAP-78030
    "django>=5.2.17,<5.3",  # minimum version enforced to address AAP-85800
    "django-prometheus>=2.0.0",
    "social-auth-core>=4.4.2",
    "social-auth-app-django>=5.2.0",
    "django-auth-ldap==4.0.0",
    "drf-spectacular",
    "dynaconf>=3.2.13",
    "insights_analytics_collector>=0.3.0",
    "boto3",
    "distro",
    "django-flags>=5.0.13",
    "django-ansible-base[jwt-consumer,feature-flags] @ git+https://github.com/ansible/django-ansible-base@e5a492d23705be7a6a22a9047ac3e4a0b3a25493",
    "django-crum==0.7.9",
    "django-automated-logging~=6.2",
    "django-storages[azure,boto3,s3]",
    "aiohttp>=3.14.3",
    "aiodns>=3.3.0,<3.7",  # aligned with pulpcore; >=3.3 required to fix hanging issue
    "setuptools<=81",  # declare here to ensure it's included in the RPM system
    "pillow>=12.3.0",  # minimum version enforced to address AAP-82156
    "cryptography>=46.0.7",  # minimum version enforced to address AAP-75045
    "pyopenssl>=25.3.0",  # bumped to allow cryptography>=46.0.5
    "black>=26.3.1",  # minimum version enforced for AAP-68431, AAP-68430, AAP-68421
    "ansible-lint>=26.1.1",  # minimum version enforced for AAP-68431, AAP-68430, AAP-68421
    "pyasn1>=0.6.4",  # minimum version enforced to address AAP-69046, AAP-69045, AAP-69038
    # Needed for compatibility with DAB:
    # https://github.com/ansible-automation-platform/django-ansible-base/blob/devel/requirements/requirements.in#L7
    "djangorestframework<3.16",
    "gitpython>=3.1.55",  # minimum version enforced to address AAP-86813, AAP-88589
]


# https://softwareengineering.stackexchange.com/questions/223634/what-is-meant-by-now-you-have-two-problems
def strip_package_name(spec):
    operators = ["=", ">", "<", "~", "!", "^", "@"]
    for idc, char in enumerate(spec):
        if char in operators:
            return spec[:idc]
    return spec


unpin_requirements = os.getenv("LOCK_REQUIREMENTS") == "0"
if unpin_requirements:
    """
    To enable the installation of local dependencies e.g: a local fork of
    pulp_ansible checked out to specific branch/version.
    The paths listed on DEV_SOURCE_PATH must be unpinned to avoid pip
    VersionConflict error.
    ref: https://github.com/ansible/galaxy_ng/wiki/Development-Setup
         #steps-to-run-dev-environment-with-specific-upstream-branch
    """
    DEFAULT = "pulpcore:pulp_ansible:pulp_container:galaxy_importer:django-ansible-base"
    DEV_SOURCE_PATH = os.getenv(
        "DEV_SOURCE_PATH", default=DEFAULT
    ).split(":")
    DEV_SOURCE_PATH += [path.replace("_", "-") for path in DEV_SOURCE_PATH]
    requirements = [
        strip_package_name(req) if req.lower().startswith(tuple(DEV_SOURCE_PATH)) else req
        for req in requirements
    ]
    print("Installing with unpinned DEV_SOURCE_PATH requirements", requirements)

setup(
    name=package_name,
    version=version,
    description="galaxy-ng plugin for the Pulp Project",
    long_description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="Red Hat, Inc.",
    author_email="info@ansible.com",
    url="https://github.com/ansible/galaxy_ng/",
    python_requires=">=3.11",
    setup_requires=["wheel"],
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=(
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ),
    entry_points={"pulpcore.plugin": ["galaxy_ng = galaxy_ng:default_app_config"]},
)
