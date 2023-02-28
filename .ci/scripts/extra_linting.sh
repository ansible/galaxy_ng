#!/bin/bash

EXIT_CODE=0

# Plugin template removed the call to the flake8 linter
# so we need to call it ourselves.
flake8 --config flake8.cfg || EXIT_CODE=1

exit $EXIT_CODE
