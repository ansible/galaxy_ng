DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng


.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

# ANSIBLE_SKIP_CONFLICT_CHECK=1 tells pip/pip-compile to avoid
# refusing to update ansbile 2.9 to ansible 2.10.

.PHONY: requirements
requirements:     ## Update python dependencies lock files (i.e. requirements.txt).
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/constraints.common.txt \
		setup.py
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/constraints.standalone.txt \
		setup.py requirements/requirements.standalone.in
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/constraints.insights.txt \
		setup.py requirements/requirements.insights.in


.PHONY: docker/build
docker/build:     ## Build all development images.
	./compose build


.PHONY: docker/test
docker/test:      ## Run unit tests.
	./compose run api manage test galaxy_ng.tests.unit

dev/bumpversion-patch:
	bump2version --verbose patch

dev/bumpversion-minor:
	bump2version --verbose minor

dev/bumpversion-major:
	bump2version --verbose major
