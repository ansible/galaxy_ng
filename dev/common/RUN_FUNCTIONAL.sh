#!/bin/bash -x

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

apt -y update
apt -y install git jq python3-pip docker.io libpq-dev
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

if [[ ! -f /usr/bin/python3 ]]; then
    echo "python3 not found"
    exit 1
fi
if [ ! -L /usr/local/bin/python ]; then
    ln -s /usr/bin/python3 /usr/local/bin/python
fi
which python || (echo "python symlinking did not work" && exit 1)

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

#which docker
#docker ps -a
#exit 0

#git clone https://github.com/pulp/pulp-openapi-generator /pulp-openapi-generator

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

echo "------------------------------------------- script.sh"
bash -x $GALAXY_PATH/.github/workflows/scripts/script.sh
RC=$?
if [[ $RC != 0 ]]; then
    exit $RC
fi

