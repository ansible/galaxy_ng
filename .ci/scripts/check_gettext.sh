#!/bin/bash

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../..

set -uv

MATCHES=$(grep -n -r --include \*.py "_(f")

if [ $? -ne 1 ]; then
  printf "\nERROR: Detected mix of f-strings and gettext:\n"
  echo "$MATCHES"
  exit 1
fi
