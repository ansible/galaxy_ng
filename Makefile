DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng

.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep


# Update python dependencies lock files (i.e. requirements.*.txt)

.PHONY: requirements/no-pip-upgrade
requirements/no-pip-upgrade:     ## Update based on setup.py and *.in files without asking pip for latest version
	pip-compile -o requirements/requirements.common.txt setup.py
	pip-compile -o requirements/requirements.insights.txt requirements/requirements.insights.in setup.py
	pip-compile -o requirements/requirements.standalone.txt requirements/requirements.standalone.in setup.py

.PHONY: requirements/pip-upgrade-single-package
requirements/pip-upgrade-single-package:     ## Update based on setup.py and *.in files, and parameter via pip, i.e. package=djangorestframework
	pip-compile -o requirements/requirements.common.txt setup.py --upgrade-package $(package)
	pip-compile -o requirements/requirements.insights.txt requirements/requirements.insights.in setup.py --upgrade-package $(package)
	pip-compile -o requirements/requirements.standalone.txt requirements/requirements.standalone.in setup.py --upgrade-package $(package)

.PHONY: requirements/pip-upgrade-all
requirements/pip-upgrade-all:     ## Update based on setup.py and *.in files, and all packages via pip
	pip-compile -o requirements/requirements.common.txt setup.py
	pip-compile -o requirements/requirements.insights.txt setup.py requirements/requirements.insights.in
	pip-compile -o requirements/requirements.standalone.txt setup.py requirements/requirements.standalone.in


# Repository management

.PHONY: changelog
changelog:        ## Build the changelog
	towncrier build

# Container environment management

.PHONY: docker/build
docker/build:     ## Build all development images.
	./compose build

# e.g: make docker/test TEST=.api.test_api_ui_sync_config
# if TEST is not passed run all tests.
.PHONY: docker/test
docker/test:      ## Run unit tests.
	./compose run api manage test galaxy_ng.tests.unit$(TEST)

.PHONY: docker/loaddata
docker/loaddata:  ## Load initial data from fixtures
	./compose run --rm -e PULP_FIXTURE_DIRS='["/src/galaxy_ng/dev/automation-hub"]' \
 api manage loaddata initial_data.json

.PHONY: docker/migrate
docker/migrate:   ## Run django migrations
	./compose run --rm api manage migrate

.PHONY: docker/resetdb
docker/resetdb:   ## Cleans database
	./compose run --rm api /bin/bash -c "./entrypoint.sh manage reset_db && django-admin migrate"

# Application management and debugging

# e.g: make api/get URL=/content/community/v3/collections/
.PHONY: api/get
api/get:          ## Make an api get request using 'httpie'
	# Makes 2 requests: One to get the token and another to request given URL
	http --version && (http :8002/api/automation-hub/$(URL) "Authorization: Token $$(http --session DEV_SESSION --auth admin:admin -v POST 'http://localhost:5001/api/automation-hub/v3/auth/token/' username=admin password=admin -b | jq -r '.token')" || echo "http error, check if api is running.") || echo "!!! this command requires httpie - please run 'pip install httpie'"

.PHONY: api/shell
api/shell:        ## Opens django management shell in api container
	# Tries to exec in a running container or start a containers and run
	./compose exec api django-admin shell_plus || ./compose run --use-aliases --service-ports --rm api manage shell_plus

.PHONY: api/bash
api/bash:         ## Opens bash session in the api container
	# tries to exec in a running container or start a container and run
	./compose exec api /bin/bash || ./compose run --use-aliases --service-ports --rm api /bin/bash

.PHONY: api/runserver
api/runserver:    ## Runs api using django webserver for debugging
	# Stop all running containers if any
	./compose stop
	# Start only services if containers exists, else create the containers and start.
	./compose start worker resource-manager content-app ui || ./compose up -d worker resource-manager content-app ui
	# ensure API is not running
	./compose stop api
	# Run api using django runserver for debugging
	./compose run --service-ports --use-aliases --name api --rm api manage runserver 0.0.0.0:8000

# Version / bumpversion management

# 'bumpversion path' to go from 4.1.0 -> 4.1.1
dev/bumpversion-patch:
	bump2version --verbose patch

# 'bumpversion minor' to go from 4.1.1 -> 4.2.0
dev/bumpversion-minor:
	bump2version --verbose minor

# 'bumpversion major' to go from 4.2.9 -> 5.0.0
dev/bumpversion-major:
	bump2version --verbose major

# 'bumpversion build' to go from 5.3.7.a1 -> 5.3.7.a2
dev/bumpversion-build:
	bump2version --verbose build

# 'bumpversion release' to from 5.3.7.a1 -> 5.3.7.b1
# another 'bumpversion release' to from from 5.3.7.b1 -> 5.3.7
dev/bumpversion-release:
	bump2version --verbose release
