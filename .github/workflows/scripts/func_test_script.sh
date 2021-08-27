#!/usr/bin/env bash

pytest -v -r sx --color=yes --pyargs galaxy_ng.tests.functional

# Pulp_ansible functional tests are currently disabled because of the following:
# https://github.com/ansible/galaxy_ng/actions/runs/1174487795
# E           pulpcore.client.pulp_ansible.exceptions.ApiException: (403)
# E           Reason: Forbidden
# E           HTTP response headers: HTTPHeaderDict({'Server': 'nginx/1.14.1', 'Date': 'Fri, 27 Aug 2021 14:07:52 GMT', 'Content-Type': 'text/html', 'Content-Length': '169', 'Connection': 'keep-alive'})
# E           HTTP response body: <html>

# E           <head><title>403 Forbidden</title></head>

# E           <body bgcolor="white">

# E           <center><h1>403 Forbidden</h1></center>

# E           <hr><center>nginx/1.14.1</center>

# E           </body>

# E           </html>

# /opt/hostedtoolcache/Python/3.8.11/x64/lib/python3.8/site-packages/pulpcore/client/pulp_ansible/rest.py:225: ApiException
# _______________ ERROR at setup of PulpImportTestCase.test_import _______________

## Uncomment below to re-enable Pulp_ansible functional tests

# cd ../pulp_ansible || exit
# pip install -r test_requirements.txt
# pip install .
# pytest -v -r sx --color=yes --pyargs pulp_ansible.tests.functional
# cd ..
