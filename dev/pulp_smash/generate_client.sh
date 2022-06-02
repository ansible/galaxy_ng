#!/bin/bash

set -e

declare PROJECT=$1

if [[ "$VIRTUAL_ENV" == "" ]]
then
    echo "This command must be run in a python virtual env."
    exit 1
fi

if [ ! -d "../pulp-openapi-generator/" ] 
then
    echo "Please clone github.com:pulp/pulp-smash.git into ../pulp-openapi-generator/"
    exit 1
fi

cd ../pulp-openapi-generator/

export PULP_URL=http://localhost:5001
export PULP_API_ROOT=/api/automation-hub/pulp/

./generate.sh $PROJECT python

pip install -e ../pulp-openapi-generator/$PROJECT-client
