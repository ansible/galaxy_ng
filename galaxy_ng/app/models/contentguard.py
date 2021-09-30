import hashlib
import os
import re
from url_normalize import url_normalize
from urllib.parse import urlparse

from django.db import models

from pulpcore.plugin.models import ContentGuard


def _gen_secret():
    return os.urandom(32)


class ContentRedirectContentGuard(ContentGuard):
    """
    Content guard to allow preauthenticated redirects to the content app.
    """

    TYPE = "content_redirect"

    shared_secret = models.BinaryField(max_length=32, default=_gen_secret)

    def permit(self, request):
        """
        Permit preauthenticated redirects from pulp-api.
        """
        try:
            signed_url = request.url
            validate_token = request.query["validate_token"]
            hex_salt, hex_digest = validate_token.split(":", 1)
            salt = bytes.fromhex(hex_salt)
            digest = bytes.fromhex(hex_digest)
            url = re.sub(r"\?validate_token=.*$", "", str(signed_url))
            if not digest == self._get_digest(salt, url):
                raise PermissionError("Access not authenticated")
        except (KeyError, ValueError):
            raise PermissionError("Access not authenticated")

    def preauthenticate_url(self, url, salt=None):
        """
        Add validate_token to urls query string.
        """
        if not salt:
            salt = _gen_secret()
        hex_salt = salt.hex()
        digest = self._get_digest(salt, url).hex()
        url = url + f"?validate_token={hex_salt}:{digest}"
        return url

    def _get_digest(self, salt, url):
        url_parts = urlparse(url_normalize(url))
        hasher = hashlib.sha256()
        hasher.update(salt)
        hasher.update(url_parts.path.encode())
        hasher.update(b"?")
        hasher.update(url_parts.query.encode())
        hasher.update(self.shared_secret)
        return hasher.digest()

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
