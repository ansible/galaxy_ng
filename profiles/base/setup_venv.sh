set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

pip install -r integration_requirements.txt