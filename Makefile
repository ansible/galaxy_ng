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
	ANSIBLE_SKIP_CONFLICT_CHECK=1 pip-compile -U -o requirements/requirements.common.txt \
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

.PHONY: docker/loaddata
docker/loaddata:  ## Load initial data from fixtures
	./compose run --rm -e PULP_FIXTURE_DIRS='["/src/galaxy_ng/dev/automation-hub"]' \
 api manage loaddata initial_data.json

.PHONY: docker/migrate
docker/migrate:   ## Run django migrations
	./compose run --rm api manage migrate
