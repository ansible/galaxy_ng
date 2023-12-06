import pytest
from unittest import mock
import subprocess
import tempfile
import os
import yaml
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError, ErrorDetail
from rest_framework.test import APIClient

from pulp_ansible.app.models import Collection

from galaxy_ng.app.auth.auth import TaskAuthentication
from galaxy_ng.app.tasks.ansible_builder import _create_ansible_cfg
from galaxy_ng.tests.unit.api.base import BaseTestCase
from galaxy_ng.app.models import auth, Namespace
from galaxy_ng.app.api.v3.serializers import ContainerAnsibleBuilderSerializer
from galaxy_ng.tests.unit.app.utils.collections import (
    create_repo,
    get_create_version_in_repo
)


class TestContainerAnsibleBuilderViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth.User.objects.create(
            username='foo',
            password="bar"
        )

        self.namespace = Namespace.objects.create(name='builder_namespace')
        self.collection = Collection.objects.create(
            namespace=self.namespace, name='builder_collection'
        )
        repo = create_repo(name='builder_repo')
        repository_url = reverse(
            'repositories-ansible/ansible-detail',
            kwargs={
                'pk': repo.pk
            }
        )
        self.repository = self.client.get(repository_url)
        version = "1.0.0"
        get_create_version_in_repo(
            self.namespace,
            self.collection,
            repo,
            version=version
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        self.execution_environment_yaml_dict = {
            'version': 3,
            'images': {
                'base_image': {
                    'name': 'quay.io/centos/centos:stream8'
                }
            },
            'options': {
                'user': '1000'
            },
            'dependencies': {
                'python_interpreter': {
                    'package_system': 'python39',
                    'python_path': '/usr/bin/python3.9'
                },
                'ansible_core': {
                    'package_pip': ('https://github.com/ansible/ansible/'
                                    'archive/refs/tags/v2.13.2.tar.gz')
                },
                'ansible_runner': {
                    'package_pip': 'ansible-runner==2.2.1'
                },
                'galaxy': {
                    'collections': [
                        {
                            'name': 'builder_namespace.builder_collection',
                            'version': '1.0.0'
                        }
                    ]
                }
            },
            'additional_build_files': [
                {'src': './ansible.cfg', 'dest': './'}
            ]
        }

        self.execution_environment_yaml = yaml.dump(self.execution_environment_yaml_dict)

        self.temp_dir = tempfile.mkdtemp(prefix='unittest-ansible-builder-', dir='/tmp')

        self.token = TaskAuthentication().get_token(self.admin_user.username)

        _create_ansible_cfg(self.temp_dir, self.token)

        self.temp_yaml = os.path.join(self.temp_dir, "execution-environment.yml")
        with open(self.temp_yaml, 'w') as f:
            f.write(self.execution_environment_yaml)

        process = subprocess.run(
            "ansible-builder create",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.temp_dir
        )

        self.assertEqual(process.returncode, 0)

    def test_container_ansible_builder_serializer(self):
        view = mock.Mock()

        data = {
            "destination_container_repository": None,
            "container_tag": "latest",
            "execution_environment_yaml": None,
            "source_collection_repositories": [
                "/api/galaxy/pulp/api/v3/repositories/ansible/ansible/"
                "118c2b17-1dba-7ee9-b8c9-304e99ed4528/"
            ]
        }
        # invalid serializer
        build_serializer = ContainerAnsibleBuilderSerializer(data=data, context={"view": view})

        with pytest.raises(ValidationError) as err:
            self.assertFalse(build_serializer.is_valid(raise_exception=True))

        validations = err.value.args[0]

        self.assertListEqual(
            validations["destination_container_repository"],
            [ErrorDetail(string='This field may not be null.', code='null')]
        )
        self.assertListEqual(
            validations["execution_environment_yaml"],
            [ErrorDetail(string='This field may not be null.', code='null')]
        )
        self.assertListEqual(
            validations["source_collection_repositories"],
            [
                ErrorDetail(
                    string='Invalid hyperlink - Object does not exist.',
                    code='does_not_exist'
                )
            ]
        )

        data = {
            "destination_container_repository": "new_builder_image",
            "container_tag": "1.0.0",
            "execution_environment_yaml": "--- yaml",
            "source_collection_repositories": [
                self.repository.data["pulp_href"]
            ]
        }
        # valid serializer
        build_serializer = ContainerAnsibleBuilderSerializer(data=data, context={"view": view})
        is_valid = build_serializer.is_valid(raise_exception=True)
        self.assertTrue(is_valid)

    def test_generated_tmp_builder_files(self):
        tmp_dir = os.listdir(self.temp_dir)

        self.assertListEqual(["ansible.cfg", "execution-environment.yml", "context"], tmp_dir)

        context_path = os.path.join(self.temp_dir, "context")
        context_dir = os.listdir(context_path)
        self.assertListEqual(["_build", "Containerfile"], context_dir)

        build_path = os.path.join(context_path, "_build")
        build_dir = os.listdir(build_path)

        self.assertListEqual(["scripts", "requirements.yml", "ansible.cfg"], build_dir)

    def test_requirements_file(self):
        requiremets_path = os.path.join(
            self.temp_dir,
            "context",
            "_build",
            "requirements.yml"
        )

        with open(requiremets_path, 'r') as file:
            yaml_requirements = yaml.safe_load(file)

        self.assertDictEqual(
            {'collections': [
                {'name': 'builder_namespace.builder_collection', 'version': '1.0.0'}
            ]},
            yaml_requirements
        )

    def test_create_ansible_cfg_content(self):
        ansible_cfg_path = os.path.join(
            self.temp_dir,
            "context",
            "_build",
            "ansible.cfg"
        )

        url = urljoin(settings.ANSIBLE_API_HOSTNAME, settings.GALAXY_API_PATH_PREFIX)
        example_ansible_cfg = (
            "[galaxy]\n"
            + "server_list = automation_hub\n\n"
            + "[galaxy_server.automation_hub]\n"
            + f"url={url}\n"
            + f"token={self.token}\n"
        )

        with open(ansible_cfg_path, 'r') as file:
            ansible_cfg = file.read()

        self.assertEqual(example_ansible_cfg, ansible_cfg)
