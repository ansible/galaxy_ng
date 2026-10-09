#!/usr/bin/env python3

from setuptools import find_packages, setup


setup(
    name="galaxy-ng",
    version="4.12.0dev",
    description="galaxy-ng plugin for the Pulp Project",
    long_description="galaxy-ng plugin for the Pulp Project",
    license="GPLv2+",
    author="Red Hat, Inc.",
    author_email="info@ansible.com",
    url="https://github.com/ansible/galaxy_ng/",
    python_requires=">=3.12",
    setup_requires=["wheel"],
    install_requires=[
        "galaxy-importer>=0.4.31,<0.5.0",
        "pulpcore>=3.105.21,<3.106",
        "pulp_ansible>=0.30.1,<0.31",
        "pulp-container>=2.27.11,<2.28",
        "pyjwt[crypto]>=2.14.0",  # minimum version enforced to address 94872
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
        "pillow>=12.3.0",  # minimum version enforced to address AAP-82156
        "cryptography>=46.0.7",  # minimum version enforced to address AAP-75045
        "pyopenssl>=25.3.0",  # bumped to allow cryptography>=46.0.5
        "black>=26.3.1",  # minimum version enforced for AAP-68431, AAP-68430, AAP-68421
        "ansible-lint>=26.1.1",  # minimum version enforced for AAP-68431, AAP-68430, AAP-68421
        "pyasn1>=0.6.4",  # minimum version enforced to address AAP-69046, AAP-69045, AAP-69038
        # Needed for compatibility with DAB:
        # https://github.com/ansible-automation-platform/django-ansible-base/blob/devel/requirements/requirements.in#L7
        "djangorestframework<3.16",
        "gitpython>=3.1.60",  # minimum version enforced to address AAP-92294, AAP-92292,AAP-92284
    ],
    include_package_data=True,
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=(
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ),
    entry_points={"pulpcore.plugin": ["galaxy_ng = galaxy_ng:default_app_config"]},
)
