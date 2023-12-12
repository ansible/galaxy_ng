import pytest

from galaxykit.utils import wait_for_task
from orionutils.generator import randstr


@pytest.mark.deployment_standalone
def test_container_ansible_builder_build_task(galaxy_client):

    container_name = f"foo_builder_image_{randstr(8)}"

    payload = {
        "execution_environment_yaml": """---
version: 3
images:
  base_image:
    name: registry.access.redhat.com/ubi9/ubi-minimal:latest

options:
  package_manager_path: /usr/bin/microdnf

dependencies:
  python_interpreter:
    package_system: python39
    python_path: /usr/bin/python3.9
  ansible_core:
    package_pip: https://github.com/ansible/ansible/archive/refs/tags/v2.13.2.tar.gz
  ansible_runner:
    package_pip: ansible-runner==2.2.1
""",
        "destination_container_repository": container_name,
        "container_tag": "latest",
        "source_collection_repositories": []
    }

    gc = galaxy_client("admin")
    build_task = gc.post(
        "v3/plugin/execution-environments/image-builder/",
        body=payload
    )

    finished_task = wait_for_task(gc, build_task)

    assert finished_task["state"] == "completed"

    ee = gc.get(f"v3/plugin/execution-environments/repositories/{container_name}/")
    assert ee["name"] == container_name


@pytest.mark.deployment_standalone
def test_container_ansible_builder_build_with_galaxy_dependencies_task(galaxy_client, published):
    gc_admin = galaxy_client("admin")

    col_search = gc_admin.get(
        "v3/plugin/ansible/search/collection-versions/"
        f"?namespace={published.namespace}&name={published.name}&version={published.version}"
    )["data"]

    assert len(col_search) == 1

    repo_href = col_search[0]["repository"]["pulp_href"]

    container_name = f"bar_builder_image_{randstr(8)}"

    payload = {
        "execution_environment_yaml": f"""---
version: 3
images:
  base_image:
    name: registry.access.redhat.com/ubi9/ubi-minimal:latest

options:
  package_manager_path: /usr/bin/microdnf

dependencies:
  python_interpreter:
    package_system: python39
    python_path: /usr/bin/python3.9
  ansible_core:
    package_pip: https://github.com/ansible/ansible/archive/refs/tags/v2.13.2.tar.gz
  ansible_runner:
    package_pip: ansible-runner==2.2.1
  galaxy:
    collections:
    - name: {published.namespace}.{published.name}
      version: {published.version}
""",
        "destination_container_repository": container_name,
        "container_tag": "latest",
        "source_collection_repositories": [
            repo_href
        ]
    }

    gc = galaxy_client("admin")
    build_task = gc.post(
        "v3/plugin/execution-environments/image-builder/",
        body=payload
    )

    finished_task = wait_for_task(gc, build_task)
    assert finished_task["state"] == "completed"

    ee = gc.get(f"v3/plugin/execution-environments/repositories/{container_name}/")
    assert ee["name"] == container_name


@pytest.mark.deployment_standalone
def test_container_ansible_builder_build_multiple_tags_task(galaxy_client):

    container_name = f"baz_builder_image_{randstr(8)}"

    payload = {
        "execution_environment_yaml": """---
version: 3
images:
  base_image:
    name: registry.access.redhat.com/ubi9/ubi-minimal:latest

options:
  package_manager_path: /usr/bin/microdnf

dependencies:
  python_interpreter:
    package_system: python39
    python_path: /usr/bin/python3.9
  ansible_core:
    package_pip: https://github.com/ansible/ansible/archive/refs/tags/v2.13.2.tar.gz
  ansible_runner:
    package_pip: ansible-runner==2.2.1
""",
        "destination_container_repository": container_name,
        "container_tag": "1.0.0",
        "source_collection_repositories": []
    }

    gc = galaxy_client("admin")
    build_task = gc.post(
        "v3/plugin/execution-environments/image-builder/",
        body=payload
    )

    finished_task = wait_for_task(gc, build_task)
    assert finished_task["state"] == "completed"

    ee = gc.get(f"v3/plugin/execution-environments/repositories/{container_name}/")
    assert ee["name"] == container_name

    ee_tags = gc.get(
        f"v3/plugin/execution-environments/repositories/{container_name}/_content/tags/"
    )["data"]

    assert len(ee_tags) == 1
    assert ee_tags[0]["name"] == "1.0.0"

    payload["container_tag"] = "1.2.3"

    build_task = gc.post(
        "v3/plugin/execution-environments/image-builder/",
        body=payload
    )
    finished_task = wait_for_task(gc, build_task)
    assert finished_task["state"] == "completed"

    ee_tags = gc.get(
        f"v3/plugin/execution-environments/repositories/{container_name}/_content/tags/"
    )["data"]

    assert len(ee_tags) == 2
    tag_names = [tag["name"] for tag in ee_tags]

    assert sorted(["1.2.3", "1.0.0"]) == sorted(tag_names)
