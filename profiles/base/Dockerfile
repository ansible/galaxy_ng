FROM localhost/oci_env/pulp:base

COPY . /opt/galaxy_ng/
WORKDIR /opt/galaxy_ng/

# preinstall galaxy_ng in thebase image
RUN pip install .

# set up venv for integration tests 
RUN pip install virtualenv && virtualenv /tmp/gng_testing
RUN bash profiles/base/setup_venv.sh