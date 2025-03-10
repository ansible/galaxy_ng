# Node Setup

Requirements:

- system has a running `gpg-agent`
- required files are in place

```bash
# Keys
/etc/pulp/certs/signing-secret.key
/etc/pulp/certs/signing-secret.key.password.tx
/etc/pulp/certs/signing-public.key

# Scripts
/var/lib/pulp/scripts/collection_sign.sh
/var/lib/pulp/scripts/container_sign.sh

# Workarounds for Pulp envvar limitation.
# required only if GPGHOME differs from running user HOME
# ./setup_gpg_workarounds.sh
/etc/pulp/certs/HOME.workaround.txt
/etc/pulp/certs/GNUPGHOME.workaround.txt
```

## Workers

```bash
./setup_gpg_keys.sh
```

## Run once, on any node, after workers are alive

```bash
./setup_gpg_keys.sh
./setup_signing_services.sh
./setup_repo_keyring.sh
```

---

# How Signing Works

## 1. GPG and keys

System needs a GPGHOME and a KEYRING

Usually:

```bash
~/.gnupg/pubring.kbx
```

> NOTE: If `GNUPGHOME` differs from the current user `HOME`, then it is required to save the path to `/etc/pulp/certs/HOME.workaround.txt` and `/etc/pulp/certs/GNUPGHOME.workaround.txt` as a workaround due to a limitation on Pulp SigningService that cannot access external environment variables.

The keyring must have the secret-key for signing and public key for verification.
The files are located on this directory and must be copied to `/etc/pulp/certs`

> These keys are for development purposes only! NEVER USE THOSE IN PRODUCTION!

- cp `signing-secret.key` -> `/etc/pulp/certs/signing-secret.key`
- cp `signing-public.key` -> `/etc/pulp/certs/signing-public.key`

Key information:

- fingerprint is `FB8B3F2D24BCAF7EFDF793A9F37575C52D4F16F3`
- short id `F37575C52D4F16F3`
- admin ID `galaxydev@ansible.com`
- passphrase `Galaxy2024`

The passphrase must be added to a file named `/etc/pulp/certs/signing-secret.key.password.txt`

```bash
echo "Galaxy2024" > /etc/pulp/certs/signing-secret.key.password.txt
```

To add both keys to the keyring start the agent and run:

```bash
gpgconf --kill gpg-agent && gpg --batch --no-default-keyring --import /etc/pulp/certs/signing-secret.key;
```

it is also require to adjust the key trust level:

```bash
(echo 5; echo y; echo save) | gpg --command-fd 0 --no-tty --no-greeting -q --edit-key 'FB8B3F2D24BCAF7EFDF793A9F37575C52D4F16F3'
```

Ensure key is added and trusted

```bash
gpg --list-secret-keys
```

Must output a `[ultimate]` trust level key.


## 2. Signing Scripts and Signing Service

> For collection the script is `collection_sign.sh` and for containers `container_sign.sh`, both
> located on this directory, the files must be copied to `/var/lib/pulp/scripts/`

- cp `collection_sign.sh` -> `/var/lib/pulp/scripts/collection_sign.sh`
- cp `container_sign.sh` -> `/var/lib/pulp/scripts/container_sign.sh`

> NOTE: The path for the signing service can be any path, `/var/lib/pulp/script` is just a convention.

Use `pulpcore-manager add-signing-service` to register the signing service.

- name: container-default | ansible-default
- script: path/to/executable that can access the GPG keyring
- key: fingerprint_of_gpg_key that lives on the keyring

Examples:

For collections:

```bash
pulpcore-manager add-signing-service ansible-default /var/lib/pulp/scripts/collection_sign.sh F37575C52D4F16F3
```

For containers:

```bash
pulpcore-manager add-signing-service container-default /var/lib/pulp/scripts/container_sign.sh F37575C52D4F16F3 --class container:ManifestSigningService;
```

> NOTE: The command above will actually try to sign an arbitrary artifact in order to validate the key.

## 3. Signing Collections and Containers

Galaxy will call the `sign` endpoint passing the following information:

- content unit id: <id of pulp content wit artifact>
- signing_service: foo
- repository: <id of the repository>

Then:

Signature content is created based on artifact and added to the same
repo as the content and contains a foreign_key to the content signed.

## 5. Public keys and Validation

### Collection

Galaxy exposes collection signature on UI and API.

### Container

For Containers the signature is added to the registry extended API so usually
clients such as `podman` will automatically fetch and validate the signature
if configured with a proper `policies.json` file.

### Public Key

When validating a signature the client `ansible-galaxy` will needs to have
the public key on a local keyring, there are 2 ways to get the public key.

- On Galaxy UI there is a menu on sidebar `Signature Keys` that exposes
the public keys and user can download it.

- On API there is the `/signing-services` API to expose the same information.

> NOTE: User needs to create the keyring locally and import the key manually.

## 6. Signature Upload

Galaxy can be alternatively configured to accept signature upload instead
of relying on a local GPG keyring and SigningService to generate it.

In this case the artifact can be externally signed (e.g using a hardware token)
and then signature uploaded during the approval dashboard process.

1. Repository needs a `gpgkey` field containing a public key.
  * `pulpcore-manager set-repo-keyring --repository staging --publickeypath /etc/pulp/certs/signing-public.key -y;`
  * OR
  * `pulpcore-manager set-repo-keyring --repository staging --keyring ~/.gnupg/pubring.kbx -y;`
2. CollectionVersion is uploaded to the repo and ends in `pending` state on approval dashboard when system has `REQUIRE_SIGNATURE_FOR_APPROVAL`
3. Signature is uploaded to the same repo, file matches the collectionversion (e.g `namespace-collection-1.2.3.asc`) name and repo uses `gpgkey` to verify the signature is valid.

In this case there is no signing service involved, no need for GPG keyrings.
