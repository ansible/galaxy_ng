---
tags:
  - on-premise
  - tech preview
---

# How to install Galaxy NG

Galaxy NG is a [Pulp plugin](https://pulpproject.org/content-plugins/). As a plugin, Galaxy_NG has multiple installation methods available.

    ```bash
    ansible-galaxy collection install pulp.pulp_installer
    ```

2. Clone the gist containing Ansible playbooks and variable files needed to complete the install into a directory called `example`:

    ```bash
    git clone https://gist.github.com/629ba52d68301cc9798227b87704df84.git example
    ```

3. Set your working directory to the `example` directory created above ex: `cd example`.

4. Within the variable file `enduser-install-vars.yml` change the value of `pulp_default_admin_password` (initial password for the Pulp admin user).


5. Install Pulp Installer role dependencies by running the following commands to download roles from [Community Galaxy](https://galaxy.ansible.com):

    ```bash
    ansible-galaxy install -r ~/.ansible/collections/ansible_collections/pulp/pulp_installer/requirements.yml
    ```

Finally, you will run the `enduser-install.yml` playbook. The following sections describe two different ways to run the playbook, depending on whether you wish to install from Python packages or from RPMs.


???+ "Install using Python packages"

     The following provides an example of how to start playbook execution. It assumes an inventory file called `hosts` exists in the current directory and contains the target host(s) where Galaxy server is to be installed:

    ```bash
    ansible-playbook enduser-install.yml -i hosts --extra-vars "@enduser-install-vars.yml"
    ```

??? "Install using upstream RPMs"

    The following provides an example of how to start playbook execution. It assumes an inventory file called `hosts` exists in the current directory and contains the target host(s) where Galaxy server is to be installed:

    ```bash
    ansible-playbook enduser-install.yml -i hosts --extra-vars "@upstream-rpm-install-vars.yml"
    ```

!!! tip
    For more information about inventory files, view [Intro to Ansible Inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)

### Logging in

By default the local Galaxy NG server is listening on port 80. Point your browser to the host where the server was installed, and a login page will be presented. For example, point your browser to https://127.0.0.1

In the login dialog, use "`admin`" as the username, and the password supplied in your playbook. This is the value of `pulp_default_admin_password`.

### Uploading a collection

Once logged in, you will be taken to the Collections page, and presented with an empty list. Since the server was just installed, and the database is empty, there are no collections to display.

!!! info
    If you need an example collection, we suggest downloading [this demo collection from Community Galaxy](https://galaxy.ansible.com/newswangerd/collection_demo). Click the [Download tarball](https://galaxy.ansible.com/download/newswangerd-collection_demo-1.0.11.tar.gz) link, and save it to your local file system. As you follow the steps in the *Create a namespace* section below, use *newswangerd* for the namespace name.


### Create a namespace
To publish a collection to the server, you will first need a namespace. Create a new namespace using the following steps:

1. Click on the *Namespaces* menu.
2. Click the *Create* button at the top of the page.
3. In the resulting dialog, enter a value for the *Name*. The value you enter must match the namespace value in the collection archive metadata that you will be publishing.
4. Leave the *Namespace Owners* field blank.
5. Click the *Create* button.

### Upload the archive
With the new namespace created, you will be taken to a page showing the collections available in the namespace. To publish the first collection, click on the *Upload collection* button in the top-right corner of the page. Using the dialog, choose the collection archive file from the local file system.

The collection archive will upload, and an import job will be started. You will be taken to the *My Imports* page where you can view the job output as it runs. During the import process the server analyzes the archive metadata, unpacks the archive, and analyzes the content.

View the new collection by clicking on the *Collections* menu option. The *Collections* page now contains a clickable tile for the newly published collection.

!!! important
    If the system is configured to require approvals the collection will not be automatically published but will wait for approval on `staging` repository.

### Publish an archive using the CLI
With [Ansible](https://github.com/ansible/ansible) installed, you can publish a collection to the Galaxy server using the `ansible-galaxy` command. Below are the steps to follow:

1. If you have not already done so, log into the Galaxy server using your web browser and create a namespace as described above.
2. Click on the *API Token* menu, and click *Load Token* button. You will copy and paste the token value into an  `ansible.cfg` file in the next step.
3. In the same directory as the collection archive file, create an `ansible.cfg` file that contains the following, setting the correct server name or IP address in the *url* value, and setting the *token* value to the token displayed in step 2 above:

   ```ini
   [galaxy]
   server_list = local_server

   [galaxy_server.local_server]
   url=https://localhost/api/galaxy/
   token=your-token-here
   ```
4. In the directory containing your collection archive and `ansible.cfg` file, run the publish command. The following shows an example:

   ```bash
   ansible-galaxy collection publish newswangerd-collection_demo-1.0.10.tar.gz --ignore-certs
   ```
   ```
   Publishing collection artifact 'newswangerd-collection_demo-1.0.10.tar.gz' to local_server http://localhost/api/galaxy/
   Collection has been published to the Galaxy server local_server http://localhost/api/galaxy/
   Waiting until Galaxy import task http://localhost/api/galaxy/v3/imports/collections/b8155faf-e6af-4873-9cf0-ce4c8b30e166/ has completed
   Collection has been successfully published and imported to the Galaxy server local_server http://localhost/api/galaxy/
   ```

#### Running admin commands

If you need to run Django admin commands, use `pulpcore-manager` by doing the following:

1. Switch to the `pulp` user:

    ```bash
    sudo su - pulp --shell /bin/bash
    ```
2. Set the `PULP_SETTINGS` variable:

    ```bash
    export PULP_SETTINGS=/etc/pulp/settings.py
    ```

3. Run `pulpcore-manager`:

    ```bash
    /usr/local/lib/pulp/bin/pulpcore-manager
    ```

### Working with the importer

The process that imports collections into Galaxy is the [galaxy-importer](https://github.com/ansible/galaxy-importer). During installation a packaged version of *galaxy-importer* is installed from PyPi.

On the Galaxy server host, run the following to see which is installed:

```bash
source /usr/local/lib/pulp/bin/activate
pip list | grep galaxy-importer
```

#### Running Importer from source

To run the latest code, or to test a pull request or an experimental branch, it might be desirable to use the source project directly.

On the Galaxy server host, clone the project. Make sure to put it in a directory that the `pulp` user can access, and set the ownership to  `pulp:users`. For example, as the root user:

```bash
cd /usr/local/lib/pulp
git clone https://github.com/ansible/galaxy-importer.git
chown -R pulp:users galaxy-importer
```

As the root user, run the following to install the source copy and replace the packaged version:

```bash
source /usr/local/lib/pulp/bin/activate
cd /usr/local/lib/pulp/galaxy-importer
pip install --upgrade -e .
```

Restart the Pulp services:

```bash
systemctl restart pulp*
```

##### Configuring and running ansible-test

As the root user, create the directory `/etc/galaxy-importer`, and within this directory create the file `galaxy-importer.cfg`. The following is a sample configuration file:

```ini
[galaxy-importer]
LOG_LEVEL_MAIN = INFO
RUN_FLAKE8 = False
RUN_ANSIBLE_TEST = False
INFRA_OSD = False
```

If you wish to run `ansible-test` during collection import, set `RUN_ANSIBLE_TEST = True`. By default `ansible-test` will be executed directly, which requires having [Ansible](https://github.com/ansible/ansible) installed. It's also possible to run `ansible-test` sandboxed in a container image using the following options:

* `ANSIBLE_TEST_LOCAL_IMAGE` - Set to `True`, if `ansible-test` should be executed in a container image. Requires having Docker installed. Defaults to `False`.

Changing the configuration does not require restarting Pulp services. Each time the importer runs, it reads the configuration and responds accordingly.

##### Using docker to run ansible-test

Using docker may require modifying the system firewall configuration to allow DNS queries between the daemon and running containers. For example, on a vanilla Centos 8 system:

```bash
# Masquerading allows for docker ingress and egress (the juicy bit)
firewall-cmd --zone=public --add-masquerade --permanent

# Specifically allow incoming traffic on port 80/443 (nothing new here)
firewall-cmd --zone=public --add-port=80/tcp
firewall-cmd --zone=public --add-port=443/tcp

# Reload firewall to apply permanent rules
firewall-cmd --reload

# Restart the Docker daemon
systemctl restart docker
```

And since the Pulp task system user the `docker` command to interact with the docker daemon, the `pulp` user needs to be added to the `docker` group. The following is an example taken from a Centos 8 system:

```bash
usermod -a -G docker pulp
```
