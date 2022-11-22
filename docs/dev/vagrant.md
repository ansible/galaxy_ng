# Run Galaxy NG using the Pulp Developer Environment

[Pulp Installer](https://pulp-installer.readthedocs.io/en/latest/pulplift/) is a vagrant configuration based on [forklift](https://github.com/theforeman/forklift).

## Setup the environment

### Requirements

- Python 3+
- Ansible 2.9+
- Vagrant 1.8+
- Vagrant [provider plugin] (https://www.vagrantup.com/docs/providers/installation.html)
- Libvirt or Virtualbox
- Vagrant SSHfs
- Enabled virtualization in BIOS

### 1. Install Vagrant and its plugins

#### On a fedora system

```bash
sudo dnf install ansible vagrant-libvirt vagrant-sshfs @virtualization
```

#### On a debian system

```bash
# virtualbox (requires sid in sources)
sudo apt install ansible vagrant vagrant-sshfs virtualbox/sid

# libvirt
sudo apt install ansible vagrant vagrant-sshfs vagrant-libvirt dnsmasq libvirt-clients libvirt-daemon libvirt-dbus qemu-system-x86 qemu-utils
sudo usermod -aG libvirt,libvirt-qemu,libvirtdbus $USER
```

#### On a Mac

```bash
brew install ansible
brew cask install virtualbox
brew cask install vagrant
```

#### On other host systems
Refer to the package manager and search for equivalent packages. For example, `pacman -S vagrant`

#### Install vagrant plugins

Required vagrant plugins:

```bash
vagrant plugin install vagrant-sshfs
```

**Optional** plugins:

```bash
vagrant plugin install vagrant-libvirt       # to connect to libvirt 
vagrant plugin install vagrant-hostmanager   # to manage local dns
```

### 2. Clone the repositories from source

!!! tip
    replace `:pulp/` and `:ansible/` with your own github username if you plan to work on your own forks. 

```bash
# required
git clone git@github.com:pulp/pulp_installer
git clone git@github.com:pulp/pulp_ansible.git
git clone git@github.com:pulp/pulp_container.git
git clone git@github.com:ansible/galaxy_ng.git
git clone git@github.com:pulp/pulpcore.git

# optional
git clone git@github.com:ansible/galaxy-importer.git
git clone git@github.com:ansible/ansible-hub-ui.git
```

Ensure repositories are located on the same folder level

```bash
$ tree -a -L 1
.
├── ansible-hub-ui/
├── galaxy-importer/
├── galaxy_ng/
├── pulp_ansible/
├── pulp_container/
├── pulpcore/
└── pulp_installer/
```

In order to avoid version conflicts, each component has to be checked out with a version of the plugin that is compatible with galaxy_ng. These versions can be found in [setup.py](https://github.com/ansible/galaxy_ng/blob/master/setup.py) under the `requirements` list. In setup.py find the following versions:

- pulpcore
- pulp_ansible
- pulp_container

```bash
cd pulpcore
git checkout <PULPCORE_VERSION>
cd ../pulp_ansible
git checkout <PULP_ANSIBLE_VERSION>
cd ../pulp_container
git checkout <PULP_CONTAINER_VERSION>
cd ..
```

### 3. Set your working directory to the `pulp_installer` directory

```bash 
cd pulp_installer
```

### 4. make sure you're running the latest compatible version of pulp_installer.

```bash
git checkout <PULPCORE_VERSION>
``` 

### 5. Initialize submodules

```bash
git submodule update --init
```

### 6. Create the installer config file

In the root of the `pulp_installer` directory create a new file named `local.dev-config.yml` with the following contents.

!!! Tip
    If you don't want to run pulpcore or one of the plugins from source, you can comment out `source_dir`  under `pulp_install_plugins` and add `version` or comment out `pulp_source_dir` and add `pulpcore_version`.

!!! Tip
    Documentation for the variables in this config can be found [here](https://docs.pulpproject.org/pulp_installer/roles/pulp_common/).

```yaml
---
# Pulp plugins and Python libs
pulp_install_plugins:
  pulp-ansible:
    source_dir: "/home/vagrant/devel/pulp_ansible"
    # version: "<PULP_ANSIBLE_VERSION>"
  pulp-container:
    source_dir: "/home/vagrant/devel/pulp_container"
    # version: "<PULP_CONTAINER_VERSION>"
  galaxy-ng:
    source_dir: "/home/vagrant/devel/galaxy_ng"
  # Uncomment this to run galaxy-importer from source. Other python libs can be installed like this
  # as well.
  # galaxy-importer:
  #   source_dir: "/home/vagrant/devel/galaxy-importer"

# Pulp configuration

pulp_source_dir: "/home/vagrant/devel/pulpcore"
pulp_pip_editable: true
# pulpcore_version: "<PULPCORE_VERSION>"
pulp_devel_supplement_bashrc: true
pulp_default_admin_password: password
pulp_webserver_disable_https: true
pulp_user: "vagrant"
developer_user: "vagrant"
developer_user_home: "/home/vagrant"
pulp_workers: 4
pulp_api_workers: 4
pulp_settings:
  secret_key: "unsafe_default"
  content_origin: "http://{{ ansible_fqdn }}"
  x_pulp_api_host: 127.0.0.1
  x_pulp_api_port: 24817
  x_pulp_api_user: "admin"
  x_pulp_api_password: "{{ pulp_default_admin_password }}"
  x_pulp_api_prefix: "pulp_ansible/galaxy/automation-hub/api"
  galaxy_require_content_approval: False
  pulp_token_auth_disabled: True
  galaxy_api_default_distribution_base_path: "published"
  allowed_export_paths: ["/tmp"]
  allowed_import_paths: ["/tmp"]
  ansible_api_hostname: "http://{{ ansible_fqdn }}"

# Galaxy Configuration
# Set this __galaxy variables according to your needs.
# __galaxy_profile: 'insights'or 'standalone'
__galaxy_profile: 'standalone'
# __galaxy_dev_source_path: `:` separated relative paths to the repos you cloned.
__galaxy_dev_source_path: 'pulpcore:pulp_ansible:pulp_container:galaxy_ng:galaxy-importer'
# __galaxy_lock_requirements: Set to 0 to avoid pinning of galaxy_ng/setup.py versions
__galaxy_lock_requirements: '1'

# options: precompiled, source, none
# __galaxy_ui_source: precompiled
```

!!! warning
    When provisioning the VM you can see errors such as `Version Conflict Error` and those errors are all related to set the correct version/branch/tag on each repo.

### 7. Start the vagrant VM

Use of the the [available boxes](https://github.com/pulp/pulp_installer/blob/main/vagrant/boxes.d/30-source.yaml) or run `vagrant status` to see the list of available boxes.

Example:

!!! note
    The following commands must run inside `pulp_installer` directory.

```bash
vagrant up --provider=libvirt VAGRANT_BOX_NAME  # recommended
vagrant up --provider=libvirt pulp3-source-centos8   # if you need RHEL specific features
```

> The above command will use `--provider` to provision a Vm and you use `libvirt` or `virtualbox`, ensure the respective service is running and accessible. Then it will use `local.dev-config.yml` to configure the VM.

You can use the virtualbox application or virt-manager to check the state of the VM or run `vagrant status VAGRANT_BOX_NAME`

!!! note
    The `libvirt` plugin is not available on all platforms, skip `--provider=libvirt` if things break.

!!! warning 
    This command may take several minutes to run, it may ask your root password and in case of `Version Conflict Error` refer to https://github.com/ansible/galaxy_ng/wiki/Installing-from-source---development-environment/_edit#2-clone-the-repositories-from-source step.

!!! Warning
    Vagrant silently ignores `--provider=...` if user before `up`. The right syntax is `vagrant up --provider=...`, not ~~`vagrant --provider=... up`~~.

## 8. Access Galaxy NG and PULP

**Pulp-Installer** will expose the services on the DNS `<box-name>.localhost.example.com` for example, if you installed on a fedora system 
it will be http://VAGRANT_BOX_NAME.localhost.example.com/ui/

If you installed `vagrant-hostmanager` you can then run `vagrant hostmanager` to update your hosts file.

Otherwise you will need to add manually to the `/etc/hosts` file. run `vagrant ssh VAGRANT_BOX_NAME` to connect to the VM and then `ifconfig` to see its ip address and then. 

```
# /etc/hosts
...
192.168.121.51 VAGRANT_BOX_NAME.localhost.example.com
```

To enter the **SSH** just run `vagrant ssh VAGRANT_BOX_NAME` 

The http server will either listen on `http://VAGRANT_BOX_NAME.localhost.example.com` (port 80), or on `http://localhost:8080`.


### 9. Optional - Switch to the source version of `galaxy-importer` by doing the following:

    ```
    ## SSH into the vagrant box: 
    $ vagrant ssh VAGRANT_BOX_NAME
    
    ## Within the vagrant box, install the local copy of `galaxy-importer` and restart Pulp:
    $ source /usr/local/lib/pulp/bin/activate
    $ cd /home/vagrant/devel/galaxy-importer
    $ pip install --upgrade -e .
    $ prestart
    ```

### 10. Optional - Enable running `ansible-test` during Collection import:

    ```
    # SSH into the vagrant guest:
    $ vagrant ssh pulp-source-fedora32

    # Install podman-docker
    $ sudo yum install podman-docker

    # Configure galaxy-importer
    $ sudo mkdir /etc/galaxy-importer
    ```

    Copy the following to `/etc/galaxy-importer/galaxy-importer.cfg`

    ```
    [galaxy-importer]
    LOG_LEVEL_MAIN = INFO
    RUN_FLAKE8 = True
    RUN_ANSIBLE_TEST = True
    INFRA_LOCAL_IMAGE = True
    INFRA_LOCAL_DOCKER = False
    INFRA_OSD = False
    ```

### 11. SSH into the Box

Now that everything is running, you can SSH into the box with `vagrant ssh VAGRANT_BOX_NAME` and begin development work. Once you're in you can run

- `pjournal`: shows the server logs
- `prestart`: restarts pulp

Keep in mind that the server has to be restarted any time changes are made to the code.

#### Tips and tricks

The installation comes with some useful [dev aliases](https://docs.pulpproject.org/pulp_installer/roles/pulp_devel/#aliases), once in a `vagrant ssh` session you can:

Activate pulp virtualenv

```bash
workon pulp
```

* `phelp`: List all available aliases.
* `pstart`: Start all pulp-related services
* `pstop`: Stop all pulp-related services
* `prestart`: Restart all pulp-related services
* `pstatus`: Report the status of all pulp-related services
* `pdbreset`: Reset the Pulp database - **THIS DESTROYS YOUR PULP DATA**
* `pclean`: Restore pulp to a clean-installed state - **THIS DESTROYS YOUR PULP DATA**
* `pjournal`: Interact with the journal for pulp-related unit
* `reset_pulp2`: Resets Pulp 2 - drop the DB, remove content and publications from FS, restart services.
* `populate_pulp2_iso`: Syncs 4 ISO repos.
* `populate_pulp2_rpm`: Sync 1 RPM repo.
* `populate_pulp2_docker`: Sync 1 Docker repo.
* `populate_pulp2`: Reset Pulp 2 and sync ISO, RPM, Docker repos.
* `pyclean`: Cleanup extra python files
* `pfixtures`: Run pulp-fixtures container in foreground
* `pbindings`: Create and install bindings. Example usage: `pbindings pulpcore python`
* `pminio`: Switch to minio for S3 testing. For stopping it: `pminio stop`

## Running tests

Functional and unit tests can be run from vagrant. Integration tests can only be run in [the docker environment](dev/docker_environment.md).

### Integration Tests

1. SSH into the vagrant box `vagrant ssh YOUR_BOX_NAME`
2. Activate the python virtual env `workon pulp`
3. cd to the plugin you want to test `cd ~/devel/pulp_ansible/`
4. Install the testing requirements `pip install -r functest_requirements.txt`
5. Build the pulp bindings `pbindings pulp_ansible python`
6. Run the tests `pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.functional`

!!! note
    Any time the APIs change, the server needs to be restarted with `prestart` and the bindings have to be rebuilt with `pbindings PLUGIN_NAME python`

!!! warning
    Some pulp_ansible tests require extra setup and others will always fail if galaxy_ng is installed.

!!! tip
    You can run a single test by passing `-k my_test_name` to the pytest command.

### Unit Tests

1. SSH into the vagrant box `vagrant ssh YOUR_BOX_NAME`
2. Activate the python virtual env `workon pulp`
3. cd to the plugin you want to test `cd ~/devel/pulp_ansible/`
4. Install the testing requirements `pip install -r unittest_requirements.txt`
5. Run the tests `pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.unit`

## Troubleshooting

### Centos 8

When using Centos 8, [there's currently a bug](https://github.com/dustymabe/vagrant-sshfs/pull/111) in `vagrant-sshfs` that causes the `fuse-sshfs` package to not install in the guest. Until that gets fixed, best to use Fedora 31+ to test an Enterprise Linux distro.

To use Centos 8 with Virtualbox (assuming the `vagrant-sshfs` issue is fixed), check `vagrant/boxes.d/30-source.yaml` to see if the box being referenced points to a URL. If so, take a look at `https://cloud.centos.org/centos/8-stream/x86_64/images/`, and update the URL to reference an image that's compatible with Virtualbox. The delivered URL was pointing to a Libvirt compatible box.

### Centos 7

If using Centos 7 with a clone of the `ansible-hub-ui` project, the UI will not build without first upgrading the version of Node. This might be accomplished by adding an inline script to the config section of the `Vagrantfile`. Otherwise, expect the build to fail :-(

`Call to virConnectOpen failed: Failed to connect socket to '/var/run/libvirt/libvirt-sock': No such file or directory` - `libvirtd` or `libvirt-daemon-system` needs to be installed and running

`Call to virConnectOpen failed: authentication unavailable: no polkit agent available to authenticate action 'org.libvirt.unix.manage'` - the current user needs to be a member of the `libvirt` system group

### Running vagrant on MacOS

In some cases, the default `pulp3-source-fedoraXX` boxes don't work on MacOS. Custom pulp boxes can also be created by adding a `pulp_installer/vagrant/boxes.d/99-local.yaml` file. The `generic/fedoraXX` boxes seem to work reliably well on MacOS and can be created like so:

```yaml
# 99-local.yaml

mycustombox:
  box_name: 'generic/fedora34'
  image_name: !ruby/regexp '/Fedora 34.*/'
  pty: true
  ansible:
    variables:
      ansible_python_interpreter: /usr/bin/python3

hub:
  box: 'mycustombox'
  sshfs:
    host_path: '..'
    guest_path: '/home/vagrant/devel'
    reverse: False
  memory: 6144
  cpus: 4
  ansible:
    playbook: "vagrant/playbooks/source-install.yml"
    galaxy_role_file: "requirements.yml"

  # The default network configuration may not work for vagrant host manager. If that's the case, assigning an IP address
  # to the box may fix the issue.
  networks:
    - type: 'private_network'
      options:
        ip: 192.168.150.5
        
```

## Working on master branches

 **I need to work on pulp_ansible or pulp_container master how do I do?**

If you need to work on pulp_ansible,pulpcore or pulp_container master branches do the following:

1. first do the normal provisioning using compatible versions/tags/branched *described above*
2. ssh in to the VM `vagrant ssh VAGRANT_BOX_NAME`
3. stop pulp serviced `pstop`
4. go to the repo and checkout to the desired branch or tag, you can do that inside VM in `/home/vagrant/devel` or on your local host directory as they are mounted inside VM.
5. Run `workon pulp` inside the VM ssh session and then run `django-admin migrate` and resolve any conflict
6. restart pulp services `pstart`


## Some Handy Bash aliases

If you're like me and you can't be bothered to remember the commands for starting and stopping vagrant boxes, here are some handy aliases that you can add to your bash profile.

```bash
# Set the path to the directory that contains pulp_installer, galaxy_ng, pulpcore etc.
HUB_BASE_PATH="/path/to/your/pulp/source"

# Set the pulp box you wish to use
PULP_BOX="VAGRANT_BOX_NAME"

# Start the vagrant box if it is already provisioned
alias pulp_up="cd ${HUB_BASE_PATH}/pulp_installer && SSH_AUTH_SOCK= vagrant up ${PULP_BOX}"

# Re provision the vangant box
alias pulp_provision="cd ${HUB_BASE_PATH}/pulp_installer && SSH_AUTH_SOCK= vagrant up --provision ${PULP_BOX}"

# Destroy the current vagrant box
alias pulp_destroy="cd ${HUB_BASE_PATH}/pulp_installer && SSH_AUTH_SOCK= vagrant destroy -f ${PULP_BOX}"

# SSH into the vagrant box
alias pulp_ssh="cd ${HUB_BASE_PATH}/pulp_installer && SSH_AUTH_SOCK= vagrant ssh ${PULP_BOX}"

# Stop the vagrant box from running
alias pulp_stop="cd ${HUB_BASE_PATH}/pulp_installer && SSH_AUTH_SOCK= vagrant halt ${PULP_BOX}"
```
