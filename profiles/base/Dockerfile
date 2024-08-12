FROM localhost/oci_env/pulp:base

# Define the build argument
ARG DJANGO_ANSIBLE_BASE_BRANCH=devel

# Set the environment variable based on the build argument
ENV DJANGO_ANSIBLE_BASE_BRANCH=${DJANGO_ANSIBLE_BASE_BRANCH}

RUN echo "fastestmirror=1" >> /etc/dnf/dnf.conf

COPY . /opt/galaxy_ng/
WORKDIR /opt/galaxy_ng/

# override the image's nginx templating scripts ...
RUN cp -p /opt/galaxy_ng/profiles/base/nginx/template_nginx.py /nginx/.
RUN cp /opt/galaxy_ng/profiles/base/nginx/nginx.conf.j2 /nginx/.

# preinstall galaxy_ng in thebase image
RUN python3.11 -m pip install .

# set up venv for integration tests 
RUN python3.11 -m pip install virtualenv && python3.11 -m venv /tmp/gng_testing
RUN bash profiles/base/setup_venv.sh

WORKDIR /
