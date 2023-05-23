from galaxy_ng.tests.integration.utils import (
    wait_for_task, wait_for_all_tasks
)


class PulpObjectBase:
    """
    A base class that provides an easier interface for interacting
    with the pulp apis via the galaxy ng test client. Provides:
    """
    def __init__(self, client):
        self.client = client
        self.api_prefix = client.config.get("api_prefix")
        self.cleanup_hrefs = []

    def cleanup(self):
        for href in self.cleanup_hrefs:
            try:
                self.client(href, method="DELETE")
            except:  # noqa
                pass

        wait_for_all_tasks(self.client)

        self.cleanup_hrefs = []

    def __del__(self):
        self.cleanup()


class AnsibleDistroAndRepo(PulpObjectBase):
    def __init__(self, client, name, repo_body=None, distro_body=None):
        super().__init__(client)

        repo_body = repo_body or {}
        distro_body = distro_body or {}

        self._repo_body = {
            "name": name,
            **repo_body
        }

        self._distro_body = {
            "name": name,
            "base_path": name,
            **distro_body
        }

        self.create()

    def create(self):
        self._repo = self.client(
            f"{self.api_prefix}pulp/api/v3/repositories/ansible/ansible/",
            args=self._repo_body,
            method="POST"
        )

        resp = self.client(
            f"{self.api_prefix}pulp/api/v3/distributions/ansible/ansible/",
            args={
                "repository": self._repo["pulp_href"],
                **self._distro_body
            },
            method="POST"
        )

        wait_for_task(self.client, resp)

        self._distro = self.client(
            f"{self.api_prefix}pulp/api/v3/distributions/ansible/ansible/"
            f"?name={self._repo_body['name']}",
        )["results"][0]

        self.cleanup_hrefs = [self._distro["pulp_href"], self._repo["pulp_href"]]

    def reset(self):
        self.cleanup()
        self.create()

    def get_distro(self):
        return self._distro

    def get_repo(self):
        return self._repo
