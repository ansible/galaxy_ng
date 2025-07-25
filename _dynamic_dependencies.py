#!/usr/bin/env python3

import os

# Version constant for the project
version = "4.11.0dev"


def get_package_name():
    """Get package name with environment variable support"""
    return os.environ.get("GALAXY_NG_ALTERNATE_NAME", "galaxy-ng")


def strip_package_name(spec):
    """Strip version constraints from package specification"""
    operators = ["=", ">", "<", "~", "!", "^", "@"]
    for idc, char in enumerate(spec):
        if char in operators:
            return spec[:idc]
    return spec


def get_dependencies():
    """Generate dependencies list with LOCK_REQUIREMENTS and DAB branch support"""

    # DAB branch logic
    django_ansible_base_branch = os.getenv('DJANGO_ANSIBLE_BASE_BRANCH', '2025.7.1')
    django_ansible_base_dependency = (
        'django-ansible-base[jwt-consumer,feature-flags] @ '
        f'git+https://github.com/ansible/django-ansible-base@{django_ansible_base_branch}'
    )

    # Base requirements
    requirements = [
        "galaxy-importer>=0.4.31,<0.5.0",
        "pulpcore>=3.49.40,<3.50.0",
        "pulp_ansible>=0.25.1,<0.26",
        "pulp-container>=2.19.2,<2.20.0",
        "django>=4.2.21,<4.3",
        "django-prometheus>=2.0.0",
        "social-auth-core>=4.4.2",
        "social-auth-app-django>=5.2.0",
        "django-auth-ldap==4.0.0",
        "drf-spectacular",
        "dynaconf>=3.2.11",
        "insights_analytics_collector>=0.3.0",
        "boto3",
        "distro",
        "django-flags>=5.0.13",
        django_ansible_base_dependency,
        "django-crum==0.7.9",
        "django-automated-logging>=6.0.0,<6.1.0",
    ]

    # LOCK_REQUIREMENTS logic
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

    return requirements


def get_setup_requires():
    """Get setup requirements"""
    return ["wheel"]


# For backward compatibility, expose these as module-level attributes
__version__ = version

# Make the functions available as module attributes for setuptools dynamic configuration
# These are evaluated at module import time to provide static values to setuptools
dependencies = get_dependencies()
setup_requires = get_setup_requires()
name = get_package_name()
