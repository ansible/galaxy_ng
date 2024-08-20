#!/bin/bash

set -e

if [[ ! -d pulp-oci-images ]]; then
    git clone https://github.com/pulp/pulp-oci-images
fi
cd pulp-oci-images
git reset --hard
cd ..

cp -f switch_python pulp-oci-images/images/assets/.
chmod +x pulp-oci-images/images/assets/switch_python

cd pulp-oci-images
git apply ../py311.patch

docker build --file images/Containerfile.core.base --tag pulp/base:latest .
docker build --file images/pulp_ci_centos/Containerfile --tag pulp/pulp-ci-centos9:latest .

