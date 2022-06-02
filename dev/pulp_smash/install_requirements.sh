#!/bin/bash

set -e

declare PROJECT=$1

if [[ "$VIRTUAL_ENV" == "" ]]
then
    echo "This command must be run in a python virtual env."
    exit 1
fi

if [ ! -d "../$PROJECT/" ] 
then
    echo "Please clone $PROJECT into ../$PROJECT/"
    exit 1
fi

cd ../$PROJECT/

pip install -e .
pip install -r functest_requirements.txt