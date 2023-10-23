FROM localhost/oci_env/pulp:base
RUN echo "fastestmirror=1" >> /etc/dnf/dnf.conf

COPY . /opt/galaxy_ng/
WORKDIR /opt/galaxy_ng/

RUN switch_python 3.11

# preinstall galaxy_ng in thebase image
RUN python3.11 -m pip install .

# set up venv for integration tests 
RUN python3.11 -m pip install virtualenv && python3.11 -m venv /tmp/gng_testing
RUN bash profiles/base/setup_venv.sh

WORKDIR /
