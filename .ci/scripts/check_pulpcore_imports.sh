#!/bin/bash

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../..

set -uv

# check for imports not from pulpcore.plugin. exclude tests
MATCHES=$(grep -n -r --include \*.py "from pulpcore.*import" . | grep -v "tests\|plugin"| grep -v "pulpcore.app.*viewsets"| grep -v "pulpcore\.app.*admin"| grep -v "ProgressReportSerializer"| grep -v "pulpcore.app.*tasks"| grep -v "pulpcore.openapi.*")

if [ $? -ne 1 ]; then
  printf "\nERROR: Detected bad imports from pulpcore:\n"
  echo "$MATCHES"
  printf "\nPlugins should import from pulpcore.plugin."
  exit 1
fi
