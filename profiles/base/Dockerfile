FROM localhost/oci_env/pulp:base

COPY . /opt/galaxy_ng/
WORKDIR /opt/galaxy_ng/

RUN switch_python 3.11

# preinstall galaxy_ng in thebase image
RUN pip3.11 install .

# set up venv for integration tests 
RUN pip3.11 install virtualenv && python3.11 -m venv /tmp/gng_testing
RUN bash profiles/base/setup_venv.sh

WORKDIR /
