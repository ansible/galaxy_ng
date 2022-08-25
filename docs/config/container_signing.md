# Enabling Container Signing

Galaxy as a container registry can handle container manifest signatures, the server can accept
image push with signatures attached and can also create signatures on-demand via UI and API
using a Pulp Signing Service.


!!! tip "Enabling signing on pulp installer"
    Pulp installer can also be configured to enable container signing https://github.com/pulp/pulp_installer/tree/main/roles/galaxy_post_install#variables-for-the-signing-service
    if you configures using pulp-installer you can skip the `Creating Container Signing Service` section of this page.


### Pushing images with signatures

Pushing a tagged image altogether with its signature to the Galaxy Registry pass the `--sign-by` argument to the client.

```bash
podman push --tls-verify=false --sign-by username@email.com localhost:5001
```

### Signing Service

A signing service is an object defined on the **pulp** backend that combines a GPG **key** and the
absolute path of an executable script.

#### Creating a signing service

To create a signing service on the Galaxy server it is needed to access the `django-admin` utility
and execute:

!!! info "important"
    The command must run inside the Python Environment where galaxy_ng workers are installed.

```bash title="Bash Command"
django-admin add-signing-service \  #(1)
    unique-name \  #(2)
    /abs/path/to/script.sh \ #(3)
    GPG_KEY_ID #(4)
    --class container:ManifestSigningService #(5)
```

1. A django management command.
2. Name the signing_service should get in the database.
3. Absolute path to Shell script where the signing is performed.
4. Key id of the public key.
5. For container it is needed to inform the `--class` argument

The positional arguments to the `add-signing-service` command:

- **name**: Must be a unique name to identify the signing service object.
- **script**: Must be a path to an executable acessible and runnable by the pulp worker process user.
    One example script can be found at the pulp documentation: [https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html#metadata-signing](https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html#metadata-signing)
- **GPG_KEY_ID**: Must be the ID or e-mail that identifies the key on the global user keyring.
    The GPG key must be located at the pulp user level keyring and must be a valid GPG, there is
    a guide on how to create a valid gpg key here [https://access.redhat.com/articles/3359321](https://access.redhat.com/articles/3359321)

The named argument `--class`

- `--class` needs to be set to value `container:ManifestSigningService` so additional checks can
  be performed.


!!! important
    When importing the key to the keyring the trust level must be set to some value higher than 3.
    ex: `echo "${KEY_FINGERPRINT}:6:" | gpg --batch --import-ownertrust`


#### The signing script

Pulp Container provides an example of a script that uses **skopeo** to produce signatures
https://docs.pulpproject.org/pulp_container/workflows/sign-images.html#image-signature-configuration


!!! info
    On the running system it is important that the pulp worker has access to the `PULP_CONTAINER_SIGNING_KEY_FINGERPRINT` 
    environment variable, ex: `export PULP_CONTAINER_SIGNING_KEY_FINGERPRINT=$(gpg --show-keys --with-colons --with-fingerprint path/to/key.gpg | awk -F: '$1 == "fpr" {print $10;}' | head -n1)`

```bash title="/var/lib/pulp/scripts/container_sign.sh"
#!/usr/bin/env bash

# This GPG_TTY variable might be needed on a container image that is not running as root.
#export GPG_TTY=$(tty)

# Create a file with passphrase only if the key is password protected.
# echo "Galaxy2022" > /tmp/key_password.txt

# pulp_container SigningService will pass the next 3 variables to the script.
MANIFEST_PATH=$1
IMAGE_REFERENCE="$REFERENCE"
SIGNATURE_PATH="$SIG_PATH"

# Create container signature using skopeo
# omit --passphrase-file option if the key is not password protected.
skopeo standalone-sign \
  # --passphrase-file /tmp/key_password.txt \
  $MANIFEST_PATH \
  $IMAGE_REFERENCE \
  $PULP_CONTAINER_SIGNING_KEY_FINGERPRINT \
  --output $SIGNATURE_PATH

# Check the exit status
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo {\"signature_path\": \"$SIGNATURE_PATH\"}
else
  exit $STATUS
fi
```

#### Example

```bash title="Creating the signing service"
django-admin add-signing-service container-default \
  /var/lib/pulp/scripts/container_sign.sh \
  ${PULP_CONTAINER_SIGNING_KEY_FINGERPRINT} \
  --class container:ManifestSigningService
```

#### Configuring Galaxy to use the Signing Service

To tell galaxy which signing service to use you need to set it in the pulp settings.

Option 1:
```py title="/etc/pulp/settings.py"
GALAXY_CONTAINER_SIGNING_SERVICE = "unique-name"  #(1)
```

1. The name of the created signing service

Option 2:
```bash title="Environment Variable"
export PULP_GALAXY_CONTAINER_SIGNING_SERVICE=unique-name #(1)
```

1. The name of the created signing service

#### Signing via API

Galaxy calls Pulp Container API to trigger sign so refer to Pulp docs in case you need to
use the API for signing https://docs.pulpproject.org/pulp_container/workflows/sign-images.html#sign-images-that-were-pushed-to-the-pulp-registry

#### Signing via UI

On the UI under the **Execution Environment** menu there are buttons to trigger **sign** for a specific container image.


!!! info
    To perform signing actions the user must be a superuser (admin) or need `modify_content_containerpushrepository` permissions provided also by the Roles execution `environment admin`, `execution environment publisher`, `execution environment namespace owner`, `execution environment collaborator`

## Signature verification

### Obtaining the public key

The public keys for the signing services on a Galaxy Server are exposed on the URL https://FQDN/pulp/api/v3/signing-services/ and the respective UI page calles **Public Keys**

If the signature comes from a remote server then its public key must be found on the remote directly.

### Verification during installation

In order to verify a container image signature the client (podman, docker) needs to be configured 
with the **policy** file as described in https://github.com/containers/image/blob/main/docs/containers-policy.json.5.md

Example:

```bash
cat  /etc/containers/policy.json
{
  "default": [{"type": "reject"}],
  "transports": {
    "docker": {
       "fluffy.example.com": [
        {
          "type": "signedBy",
          "keyType": "GPGKeys",
          "keyPath": "/path-to-pupsik-key.gpg"
        }
      ]
    },
    "containers-storage": {
    "": [{"type": "insecureAcceptAnything"}] /* Allow copy operations on any images stored in containers storage (e.g. podman push) */
    }
  }
}
```

The execution of client command must be like described on https://docs.pulpproject.org/pulp_container/workflows/verify-images.html#verify-images-pushed-into-pulp-container-registry

```bash title="Client verifying container image signature" hl_lines="3 4 7 8"
podman pull fluffy.example.com/myrepo/test-image:foo
Trying to pull fluffy.example.com/myrepo/test-image:foo...
Getting image source signatures
Checking if image destination supports signatures
Copying blob 58147e24f776 skipped: already exists
Copying config 829374d342 done
Writing manifest to image destination
Storing signatures
829374d342ae65a12f3a95911bc04a001894349f70783fda841b1a784008727d
```
