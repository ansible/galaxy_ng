#!/bin/bash

EXIT_CODE=0
if (git grep "orphan_protection_time=0" ./galaxy_ng);then
    echo "Setting 'orphan_protection_time' to 0 can lead to a race condition.\n";
    EXIT_CODE=1
fi
exit $EXIT_CODE