#!/bin/bash

# Plugin template removed the call to the flake8 linter
# so we need to call it ourselves.
flake8 --config flake8.cfg

EXIT_CODE=0
if (git grep "orphan_protection_time=0" ./galaxy_ng);then
    echo "Setting 'orphan_protection_time' to 0 can lead to a race condition.\n";
    EXIT_CODE=1
fi
exit $EXIT_CODE
