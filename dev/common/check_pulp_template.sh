#!/bin/bash

# awcrosby 2022-02-25 11:15AM
#   everytime we update pulp_ansible or pulpcore we run that plugin template 
#   https://github.com/ansible/galaxy_ng/wiki/Updating-Dependencies, 
#   its worth checking if [any modified files] gets overwritten

set -e

CHECKOUT=$(pwd)
BASEDIR=$(python -c 'import tempfile; print(tempfile.mkdtemp(prefix="pulp_template_check-"))')
PLUGIN_GIT_REF=$(cat .github/template_gitref | awk -F\- '{print $NF}' | cut -dg -f2)

rm -rf $BASEDIR; mkdir -p $BASEDIR
cp -Rp $CHECKOUT $BASEDIR/galaxy_ng
git clone https://github.com/pulp/plugin_template $BASEDIR/plugin_template

cd $BASEDIR/plugin_template
git checkout $PLUGIN_GIT_REF
./plugin-template --github galaxy_ng

echo "Results ..."
cd $BASEDIR/galaxy_ng
MODIFIED_FILES=$(git status 2>/dev/null | grep 'modified:' | awk '{print $2}')
EXIT_CODE=0
for MF in $MODIFIED_FILES; do
    echo "FAILURE template-plugin would modifiy $BASEDIR/galaxy_ng/$MF"
    EXIT_CODE=1
done
if [[ $EXIT_CODE == 0 ]]; then
    echo 'SUCCESS - all files are clean'
fi
exit $EXIT_CODE
