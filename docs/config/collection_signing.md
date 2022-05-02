# Enabling Collection Signing

Galaxy Server can create, sync, receive as upload and verify and serve collection signatures.

A signature is typically a GPG ASCII Armoured Detached artifact, in other words, a file
e.g: `MANIFEST.json.asc` that is created by a GPG compatible script based on the `MANIFEST.json`
file.

The `MANIFEST.json` file already contains checksums to verify all the other artifacts inside a 
collection so that is why the signature is created based on this file. 


!!! tip "Enabling signing on pulp installer"
    Pulp installer can also be configured to enable signing https://github.com/pulp/pulp_installer/tree/main/roles/galaxy_post_install#variables-for-the-signing-service
    if you configures using pulp-installer you can skip the `Creating Signing Service` section of this page.


## Creating Signatures

Signatures can be manually created and then later uploaded to a galaxy server or the galaxy
server can internally create a signature for each collection.

### Signing Service

A signing service is an object defined on the **pulp** backend that combines a GPG **key** and the
absolute path an executable script.

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
```

1. A django management command.
2. Name, the signing_service should get in the database.
3. Absolute path to Shell script where the signing is created.
4. Key id of the public key.

The positional arguments to the `add-signing-service` command:

- **name**: Must be a unique name to identify the signing service object.
- **script**: Must be a path to an executable acessible and runnable by the pulp worker process user.
    One example script can be found at the pulp documentation: [https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html#metadata-signing](https://docs.pulpproject.org/pulpcore/workflows/signed-metadata.html#metadata-signing)
- **GPG_KEY_ID**: Must be the ID or e-mail that identifies the key on the global user keyring.
    The GPG key must be located at the pulp user level keyring and must be a valid GPG there is
    a guide on how to create a valid gpg key here [https://access.redhat.com/articles/3359321](https://access.redhat.com/articles/3359321)

!!! important
    When importing the key to the keyring the trust level must be set to some value higher than 3.  
    ex: `echo "${KEY_FINGERPRINT}:6:" | gpg --batch --import-ownertrust`


#### Configuring Galaxy to use the Signing Service

To tell galaxy which signing service to use you need to set it in the pulp settings.

Option 1:
```py title="/etc/pulp/settings.py"
GALAXY_COLLECTION_SIGNING_SERVICE = "unique-name"  #(1)
```

1. The name of the created signing service

Option 2:
```bash title="Environment Variable"
export PULP_GALAXY_COLLECTION_SIGNING_SERVICE=unique-name #(1)
```

1. The name of the created signing service


#### Configuring Galaxy to automatic sign during approval

Option 1:
```py title="/etc/pulp/settings.py"
GALAXY_AUTO_SIGN_COLLECTIONS = True  #(1)
```

1. A bool Enables automatic signing on approval

Option 2:
```bash title="Environment Variable"
export PULP_GALAXY_AUTO_SIGN_COLLECTIONS=True #(1)
```

1. On env var can be one of `true, True, 1, on, enabled`

!!! warning
    The Automatic Signing must be enabled only when `GALAXY_REQUIRE_CONTENT_APPROVAL` is `True`
    Otherwise all the content published will be signed without further checks.

??? tip "Click here for a full example script"

    ```bash
    ####################################
    # 1. Create the GPG key if not exists
    ####################################

    gpg --full-gen-key  

    # Please select what kind of key you want:
    #    (4) RSA (sign only)
    # Your selection? 4
    #
    # What keysize do you want? (2048) 
    # Requested keysize is 2048 bits
    #
    # Please specify how long the key should be valid.
    # Key is valid for? (0) 
    # Key does not expire at all
    #
    # Is this correct? (y/N) y
    #
    # Inform extra data such as Real Name, Company and email address.

    #############################################
    # 2. List the keys to fetch the KEY_FINGERPRINT
    #############################################
    # replace KEY with the key id from previous output or email.

    export KEY_FINGERPRINT=\
    $(gpg -k --with-fingerprint --with-colons KEY|awk -F: '$1 == "fpr" {print $10;}'|head -n1)

    #############################################
    # 3. Set the trust level
    #############################################

    echo "${KEY_FINGERPRINT}:6:" | gpg --batch --import-ownertrust

    #############################################
    # Create the signing script
    #############################################

    cat <<EOF >> /etc/pulp/scripts/collection_sign.sh
    #!/usr/bin/env bash

    FILE_PATH=$1
    SIGNATURE_PATH="$1.asc"

    ADMIN_ID="$KEY_FINGERPRINT"
    PASSWORD="password if needed"

    # Create a detached signature
    gpg --quiet --batch --pinentry-mode loopback --yes --passphrase \
    $PASSWORD --homedir ~/.gnupg/ --detach-sign --default-key $ADMIN_ID \
    --armor --output $SIGNATURE_PATH $FILE_PATH

    # Check the exit status
    STATUS=$?
    if [ $STATUS -eq 0 ]; then
    echo {\"file\": \"$FILE_PATH\", \"signature\": \"$SIGNATURE_PATH\"}
    else
    exit $STATUS
    fi
    EOF

    ##########################################
    # Create the signing service
    ##########################################

    django-admin add-signing-service \
    ansible-default \
    /etc/pulp/scripts/collection_sign.sh \
    $KEY_FINGERPRINT

    ################################################
    # Enable the signing service on galaxy settings
    ################################################

    echo "GALAXY_COLLECTION_SIGNING_SERVICE='ansible-default'" >> /etc/pulp/settings.py

    # OR

    export PULP_GALAXY_COLLECTION_SIGNING_SERVICE=ansible-default

    ####################################################
    # Optionally enable automatic signing upon approval
    # NOTE: this must be enabled only if 
    # `GALAXY_REQUIRE_CONTENT_APPROVAL` is True.
    ####################################################

    echo "GALAXY_AUTO_SIGN_COLLECTIONS=True" >> /etc/pulp/settings.py

    # OR

    export PULP_GALAXY_AUTO_SIGN_COLLECTIONS=True
    ```

#### Signing via API

```bash
curl -X POST \
  'http://0.0.0.0:8002/api/automation-hub/_ui/v1/collection_signing/' \  # (1)
  --header 'Authorization: Token abcdefghijklmnopqrstuvwxyz1234567890' \ # (2)
  --header 'Content-Type: application/json' \
  --data-raw '{
    "signing_service": "ansible-default",
    "distro_base_path": "staging",
    "namespace": "awx",
    "collection": "collection_name",
    "version": "0.1.0"
}'
```

1. Replace `0.0.0.0:8002` with your FQDN
2. Provide your Galaxy `API token`

!!! tip
    Omit `version` to sign entire collection  
    Omit `collection` to sign entire namespace  
    Omit `namespace` and provide to sign entire repository  
    Or provide `content_units=["*"]` or `content_units=["pulp_hrefs", ...]`

#### Signing via UI

On Galaxy UI Signing buttons are available under the pages:

- Namespace (sign entire namespace)
- Collection (sign entire collection, sign x.y.z version)
- Approval Dashboard (sign and approve, when enabled)

### Signature Upload

> **NOTE** Signature Upload doesn't require a SigningService, the server requirement is the
> existence of a keyring with the public keys to perform signature verification.

#### Enabling support for signature upload on the galaxy server

1. Set the variable `GALAXY_SIGNATURE_UPLOAD_ENABLED=True` on the setings file.
2. Create a keyring on and import the public key able to verify the signature during the upload to that keyring.  
    ```bash
    gpg --batch --no-default-keyring \
        --keyring /etc/pulp/certs/galaxy.kbx \
        --import path_to_your_public.key
    ```

3. Set the destination repositories to use the keyring.
    ```bash
    django-admin set-repo-keyring repo-name /etc/pulp/certs/galaxy.kbx
    ```
    For example, if the upload will be performed before approval, set the keyring to `staging` repo.

With the above configuration now the repository is able to accept signature uploads and verify the
signature during the upload process. 

> **NOTE** if keyring is not set, then upload will be rejected to avoid uploading invalid signatures.

!!! tip "Requiring signature for approval"
    When Signature upload is enabled and Content Approval is also enabled  
    It is possible to set `GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL=True`  
    And then the approval dashboard will allow approvals only of collections having a signature.

#### Manually Signing a Collection

Signatures can also be manually created locally and uploaded to Galaxy to be attached to a collection version.

1. Download (or build) the collection locally
2. Extract the MANIFEST.json from the collection tarball
3. Sign the collection using GPG detached with the same key as the one configured on the Galaxy Repository.
    Example:
    ```bash
    # Having the private key set locally
    # (the same private key that matched the repo keyring previously configured)
    gpg --quiet --batch --pinentry-mode loopback --yes 
    --homedir ~/.gnupg/ --detach-sign --default-key KEY_ID \
    --armor --output MANIFEST.json.asc MANIFEST.json
    ```
4. The signing generates a file `MANIFEST.json.asc` that now can be uploaded to Galaxy Server.

#### Uploading the signature via API

```bash
curl -X 'POST' \
  'http://0.0.0.0:5001/pulp/api/v3/content/ansible/collection_signatures/' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46YWRtaW4=' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@MANIFEST.json.asc;type=text/plain' \
  -F 'repository=/pulp/api/v3/repositories/ansible/ansible/43dd716c-f7dd-4a80-b889-36818ed3e347/' \
  -F 'signed_collection=/pulp/api/v3/content/ansible/collection_versions/40f85531-29a5-4eb7-b4cd-a850f8824daf/'
```

!!! warning
    This endpoint is under `/pulp/` namespace and requires the relations to be set
    using `pulp_hrefs` (full url for pulp objects)

#### Uploading the signature via UI

When enabled there will be upload buttons on the pages:

- Collection Version
- Approval Dashboard

## Syncing Signatures

When syncing from remote servers, if the signature is server Galaxy will also sync all the 
existing signatures.

Signatures are additive, so each collection can hold multiple signatures.

On galaxy `Repo Management -> Remotes` it is possible to set a remote to `sync only signed` collections

## Serving Signatures on API

Signatures are served on the `v3/content/collections` API under the `signatures` field.

## Exposing Sign State on UI

UI shows the following badges:

- Signed (All versions under the collection are signed)
- Partial (Some versions are signed but not entire collection)
- Unsigned (No versions of the collection are signed)

## Signature verification

### Obtaining the public key

The public keys for the signing services on a Galaxy Server are exposed on the URL https://FQDN/pulp/api/v3/signing-services/

If the signature comes from a remote server then its public key must be found on the remote directly.

### Verification during installation

Signature verification is performed by `ansible-galaxy` CLI.

[https://docs.ansible.com/ansible/devel/user_guide/collections_using.html#signature-verification](https://docs.ansible.com/ansible/devel/user_guide/collections_using.html#signature-verification)
