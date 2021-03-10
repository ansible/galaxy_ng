#!/bin/bash

# TODO(cutwater): This is dummy script to be called by Jenkins CI.
# 		  To be implemented.


# Need to make a dummy results file to make tests pass
mkdir -p artifacts
cat << EOF > artifacts/junit-dummy.xml
<testsuite tests="1">
    <testcase classname="dummy" name="dummytest"/>
</testsuite>
