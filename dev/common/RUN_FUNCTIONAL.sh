#!/bin/bash -x

##################################################
#   HOW TO USE ...
##################################################

# These tests expect to be run from inside the vagrant box 
# configuration shown below or on a raw ubuntu 2004 machine.

VAGRANTFILE=$(cat << EOF
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2004"
  config.vm.synced_folder ".", "/app", type: "nfs", nfs_udp: false

  config.vm.provider :libvirt do |libvirt|
    libvirt.cpus = 4
    libvirt.memory = 8092
  end

end
EOF
)

# 1) mount or copy the galaxy_ng checkout to /app/galaxy_ng
# 2) cd /app/galaxy_ng
# 3) sudo dev/common/RUN_FUNCTIONAL.sh

##################################################
#   BEGIN TESTS ...
##################################################

set -e

export TEST="pulp"
export PY_COLORS=1
export ANSIBLE_FORCE_COLOR=1
export GITHUB_PULL_REQUEST="111"
export GITHUB_PULL_REQUEST_BODY="stuff"
export GITHUB_BRANCH="master"
export GITHUB_REF="null"
export GITHUB_REPO_SLUG="galaxy_ng"
export GITHUB_CONTEXT="https://github.com/test/test"
export GITHUB_TOKEN="1111"
export GITHUB_EVENT_NAME="push"
export GITHUB_WORKFLOW="foobar"
export BRANCH="master"

export APP_PATH=/app
export GALAXY_PATH=$APP_PATH/galaxy_ng
export DEBIAN_FRONTEND=noninteractive


if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if [[ "$(cat /etc/issue)" != "Ubuntu 20.04"* ]]; then
  echo "Please run this on an Ubuntu 20.04 system"
  exit 1
fi

apt -y update
apt -y install git jq python3-pip docker.io libpq-dev
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

# Make sure docker was installed and running ...
docker ps -a
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

# /usr/bin/python is required for most things to work ...
if [[ ! -f /usr/bin/python3 ]]; then
    echo "python3 not found"
    exit 1
fi
if [ ! -L /usr/local/bin/python ]; then
    ln -s /usr/bin/python3 /usr/local/bin/python
fi
which python || (echo "python symlinking did not work" && exit 1)

# Clean up any previously created checkouts or the scripts will abort.
if [ -d $APP_PATH/pulp-smash ]; then
    rm -rf $APP_PATH/pulp-smash
fi
if [ -d $APP_PATH/pulp-openapi-generator ]; then
    rm -rf $APP_PATH/pulp-openapi-generator
fi
if [ -d $APP_PATH/pulpcore ]; then
    rm -rf $APP_PATH/pulpcore
fi
if [ -d $APP_PATH/pulp_ansible ]; then
    rm -rf $APP_PATH/pulp_ansible
fi
if [ -d $APP_PATH/pulp_container ]; then
    rm -rf $APP_PATH/pulp_container
fi
if [ -d $APP_PATH/galaxy-importer ]; then
    rm -rf $APP_PATH/galaxy-importer
fi

pip install -U pip wheel
pip install httpie

echo "------------------------------------------- before_install.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/before_install.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- install.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/install.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- install_python_client.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/install_python_client.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- install_ruby_client.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/install_ruby_client.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- before_script.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/before_script.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- secrets.py"
python3 $GALAXY_PATH/.github/workflows/scripts/secrets.py '{}'
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

echo "------------------------------------------- get registry cert"
rm -rf /etc/docker/certs.d/pulp*
mkdir -p /etc/docker/certs.d/pulp:443
openssl s_client -connect pulp:443 2>/dev/null </dev/null |  \
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /etc/docker/certs.d/pulp\:443/ca.crt

echo "------------------------------------------- script.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/script.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

