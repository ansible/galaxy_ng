DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng


.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep


.PHONY: requirements
requirements:     ## Update python dependencies lock files (i.e. requirements.txt).
	pip-compile -U -o requirements/requirements.common.txt \
		setup.py
	pip-compile -U -o requirements/requirements.standalone.txt \
		setup.py requirements/requirements.standalone.in
	pip-compile -U -o requirements/requirements.insights.txt \
		setup.py requirements/requirements.insights.in


.PHONY: docker/build
docker/build:     ## Build all development images.
	./compose build


.PHONY: docker/test
docker/test:      ## Run unit tests.
	./compose run api manage test galaxy_ng.tests.unit
