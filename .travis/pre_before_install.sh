# This file is sourced by .travis/before_install.sh

if [[ "$TRAVIS_PULL_REQUEST" != 'false' ]]; then
  pip install requests
  python .travis/custom_check_pull_request.py
fi
