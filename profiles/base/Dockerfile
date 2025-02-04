FROM localhost/oci_env/pulp:base

# Define the build argument
ARG DJANGO_ANSIBLE_BASE_BRANCH=2025.1.31

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
# This is a hotfix for bug in the rpm package postgresql-server-13.16-1.el9.x86_64
#   that doesn't create /run/postgresql directory
RUN mkdir -p /run/postgresql && chown postgres:postgres /run/postgresql

# fixes FileNotFoundError: [Errno 2] No such file or directory: \'/.ansible/roles\'
# for collection import galaxy-importer
RUN mkdir -p ~/.ansible/roles/
RUN chmod -R 775  ~/.ansible

WORKDIR /
