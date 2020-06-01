DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng


.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "requirements                Update python dependencies lock files (i.e. requirements.txt)."
	@echo ""
	@echo "Docker targets:"
	@echo "docker/build                Build all development images."


.PHONY: requirements
requirements:
	pip-compile -U -o requirements/requirements.common.txt \
		setup.py
	pip-compile -U -o requirements/requirements.standalone.txt \
		setup.py requirements/requirements.standalone.in
	pip-compile -U -o requirements/requirements.insights.txt \
		setup.py requirements/requirements.insights.in


.PHONY: docker/build
docker/build:
	./compose build
