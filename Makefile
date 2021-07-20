DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng


.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

# ANSIBLE_SKIP_CONFLICT_CHECK=1 tells pip/pip-compile to avoid
# refusing to update ansbile 2.9 to ansible 2.10.


# Update python dependencies lock files (i.e. requirements.*.txt)

.PHONY: requirements/update_local
requirements/update_local:     ## Update based on setup.py and *.in files
	pip-compile --output-file=requirements/requirements.common.txt setup.py
	pip-compile --output-file=requirements/requirements.insights.txt requirements/requirements.insights.in setup.py
	pip-compile --output-file=requirements/requirements.standalone.txt requirements/requirements.standalone.in setup.py

.PHONY: requirements/update_local_and_pip_param
requirements/update_local_and_pip_param:     ## Update based on setup.py and *.in files, and parameter via pip, i.e. package=djangorestframework
	pip-compile --output-file=requirements/requirements.common.txt setup.py --upgrade-package $(package)
	pip-compile --output-file=requirements/requirements.insights.txt requirements/requirements.insights.in setup.py --upgrade-package $(package)
	pip-compile --output-file=requirements/requirements.standalone.txt requirements/requirements.standalone.in setup.py --upgrade-package $(package)

.PHONY: requirements/update_local_and_pip_all
requirements/update_local_and_pip_all:     ## Update based on setup.py and *.in files, and all packages via pip
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile $(PIP_COMPILE_UPDATE_SPEC) -o requirements/requirements.common.txt \
		setup.py
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/requirements.standalone.txt \
		setup.py requirements/requirements.standalone.in
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/requirements.insights.txt \
		setup.py requirements/requirements.insights.in


.PHONY: docker/build
docker/build:     ## Build all development images.
	./compose build


.PHONY: docker/test
docker/test:      ## Run unit tests.
	./compose run api manage test galaxy_ng.tests.unit
