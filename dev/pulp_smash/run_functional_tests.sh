#!/bin/bash

declare PROJECT=$1

set -e

if [[ "$VIRTUAL_ENV" == "" ]]
then
    echo "This command must be run in a python virtual env."
    exit 1
fi

export XDG_CONFIG_HOME=dev/ 

pytest -r sx --color=yes --pyargs $PROJECT.tests.functional ${@:2}
