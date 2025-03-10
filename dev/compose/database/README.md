# Database Field Encryption

Pulp relies on the file `database_fields.symmetric.key` being on `/etc/pulp/certs`
For development purposes there is a hardcoded key on this folder.

```bash
mkdir -p /etc/pulp/certs/;
cp database_fields.symmetric.key /etc/pulp/certs/database_fields.symmetric.key
```

> NOTE: For development it is better to use a persistent key, so database dumps
> can be easily restored across dev environments.

## Generating a new key

```bash
rpm -q openssl || dnf -y install openssl;
mkdir -p /etc/pulp/certs/;
openssl rand -base64 32 > /etc/pulp/certs/database_fields.symmetric.key;
chmod 640 /etc/pulp/certs/database_fields.symmetric.key;
```
