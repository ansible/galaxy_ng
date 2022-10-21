import logging
from typing import Dict

from hvac import Client
from hvac.exceptions import InvalidPath
from hvac.exceptions import VaultError

log = logging.getLogger(__name__)


def _create_vault_client(settings):
    """Create and return the Vault client"""
    client = Client(
        url=settings.get("IQE_VAULT_URL"),
        verify=settings.get("IQE_VAULT_VERIFY"),
    )
    return client


def _login_and_renew_token(client, settings):
    """Log into Vault, renew the token"""
    if settings.get("IQE_VAULT_GITHUB_TOKEN"):
        client.auth.github.login(settings.get("IQE_VAULT_GITHUB_TOKEN"))
    elif settings.get("IQE_VAULT_TOKEN"):
        client.token = settings["IQE_VAULT_TOKEN"]
    elif settings.get("IQE_VAULT_ROLE_ID") and settings.get("IQE_VAULT_SECRET_ID"):
        client.auth.approle.login(
            role_id=settings["IQE_VAULT_ROLE_ID"], secret_id=settings["IQE_VAULT_SECRET_ID"]
        )
    assert client.is_authenticated(), (
        "Vault auth error, is IQE_VAULT_TOKEN, IQE_VAULT_GITHUB_TOKEN "
        "or IQE_VAULT_ROLE_ID/IQE_VAULT_SECRET_ID defined?"
    )
    client.auth.token.renew_self()
    log.info("Successfully authenticated to vault: %s", settings.get('IQE_VAULT_URL'))


class VaultSecretFetcher:
    @classmethod
    def from_settings(cls, settings):
        mountpoint = settings.get("IQE_VAULT_MOUNT_POINT") or "secret"
        if settings.get("IQE_VAULT_LOADER_ENABLED"):
            client = _create_vault_client(settings)
            _login_and_renew_token(client, settings)
        else:
            client = None
        return cls(mountpoint=mountpoint, client=client, settings=settings)

    loaded_secrets: Dict[str, Dict[str, object]]

    def __init__(self, mountpoint: str, client: Client, settings):
        self._client = client
        self._mount_point = mountpoint
        self._settings = settings
        self.loaded_secrets = {}

    def _get_path_secret_from_vault(self, path):
        if self._client is None:
            raise InvalidPath(
                f"Unable to load path '{self._mount_point}/{path}' when vault client is disabled"
            )
        if not self._client.is_authenticated():
            _login_and_renew_token(self._client, self._settings)
        try:
            data = self._client.secrets.kv.read_secret_version(path, mount_point=self._mount_point)
        except InvalidPath:
            # Give more details in the InvalidPath error message
            raise InvalidPath(f"Unable to load path '{self._mount_point}/{path}'")
        else:
            return data.get("data", {}).get("data", {})

    def _get_path_secret(self, path):
        if path not in self.loaded_secrets:
            self.loaded_secrets[path] = self._get_path_secret_from_vault(path)
        return self.loaded_secrets[path]

    def get_value_from_vault(self, path, key):
        data = self._get_path_secret(path)
        if key not in data:
            raise VaultError(f"key '{key}' not found at path '{self._mount_point}/{path}'")
        log.debug("loaded vault secret from %s/%s", self._mount_point, path)
        return data[key]
