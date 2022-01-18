#!/bin/bash

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    virtualenv $VENVPATH
    $PIP install --retries=0 --verbose --upgrade pip wheel
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

pip install -r galaxy_ng/tests/integration/requirements.txt

pytest --capture=no --pdb -m "not standalone_only" -v galaxy_ng/tests/integration
