Token API is moved from UI to v3 and now is served at ``<prefix>/v3/auth/token/``.
Token API does not support ``GET`` method anymore, token is returned to client only once after creation.
Add support of HTTP Basic authentication method to the Token API.
