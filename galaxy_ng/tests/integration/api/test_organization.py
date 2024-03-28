from galaxykit.repositories import create_repository, delete_repository

from galaxy_ng.tests.integration.utils.tools import generate_random_string


def get_pulp_id_hack(resource):
    return resource["pulp_href"].rsplit("/", maxsplit=2)[-2]


def generate_random_name(prefix='test', length=8):
    name = generate_random_string(length)
    return f"{prefix}-{name}"


def create_organization(client, name, description=''):
    response = client.post('service-index/resources/', body={
        "resource_type": "shared.organization",
        "resource_data": {
            "name": name,
            "description": description,
        }
    })
    return response


def delete_organization(client, ansible_id):
    client.delete(f'service-index/resources/{ansible_id}/', parse_json=False)


# GET {API_PREFIX}/_ui/v1/organizations/{organization_id}/repositories/
# GET {API_PREFIX}/_ui/v1/organizations/{organization_id}/repositories/{repository_id}/
# POST {API_PREFIX}/_ui/v1/organizations/{organization_id}/repositories/{repository_id}/
# DELETE {API_PREFIX}/_ui/v1/organizations/{organization_id}/repositories/{repository_id}/
def test_organization_repository_api(galaxy_client):
    client = galaxy_client("admin")

    repository = create_repository(client, generate_random_name("test-org-repo"))
    repository_id = get_pulp_id_hack(repository)

    organization = create_organization(client, generate_random_name("test-org-repo"))
    organization_id = organization["object_id"]

    response = client.get(f"_ui/v1/organizations/{organization_id}/repositories/")
    assert response["data"] == []

    org_repo_binding = client.post(
        f"_ui/v1/organizations/{organization_id}/repositories/{repository_id}/", body={}
    )

    response = client.get(f"_ui/v1/organizations/{organization_id}/repositories/")
    assert response["data"] == [org_repo_binding]

    client.delete(
        f"_ui/v1/organizations/{organization_id}/repositories/{repository_id}/",
        parse_json=False,
    )

    response = client.get(f"_ui/v1/organizations/{organization_id}/repositories/")
    assert response["data"] == []

    delete_organization(client, organization["ansible_id"])
    delete_repository(client, repository["name"])
