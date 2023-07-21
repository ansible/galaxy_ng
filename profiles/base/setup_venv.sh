set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

pip3.11 install -r integration_requirements.txt
