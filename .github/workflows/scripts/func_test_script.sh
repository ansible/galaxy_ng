#!/usr/bin/env bash
# coding=utf-8

set -mveuo pipefail

pip install ../pulp_ansible
pip install -r ../pulp_ansible/functest_requirements.txt

pytest -v -r sx --color=yes --pyargs galaxy_ng.tests.functional

cd ../pulp_ansible

pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.functional.cli
