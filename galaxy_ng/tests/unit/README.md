# Unit tests
Unit testing is done with `tox`. All necessary requirements and environment variables are set in the `tox` configuration file [tox.ini](https://github.com/ansible/galaxy_ng/blob/master/tox.ini)

Install and run `tox` tool in your virtual env:
```
python3 -m venv gng_unit_testing
source gng_unit_testing/bin/activate
pip install tox

# run unit tests
tox
```

