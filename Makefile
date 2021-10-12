.SILENT:
DOCKER_IMAGE_NAME = localhost/galaxy_ng/galaxy_ng
RUNNING = $(shell docker ps -q -f name=api)

# if running is empty, then DJ_MANAGER = manage, else DJ_MANAGER = django-admin
DJ_MANAGER = $(shell if [ "$(RUNNING)" == "" ]; then echo manage; else echo django-admin; fi)

define exec_or_run
	# Tries to run on existing container if it exists, otherwise starts a new one.
	@echo $(1)$(2)$(3)$(4)$(5)
	@if [ "$(RUNNING)" != "" ]; then \
		echo "Running on existing container $(RUNNING)" 1>&2; \
		./compose exec $(1) $(2) $(3) $(4) $(5); \
	else \
		echo "Starting new container" 1>&2; \
		./compose run --use-aliases --service-ports --rm $(1) $(2) $(3) $(4) $(5); \
	fi
endef


.DEFAULT:
.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep | sed 's/^/\n/' | sed 's/#/\n/'


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
	pip-compile -o requirements/requirements.common.txt setup.py --upgrade
	pip-compile -o requirements/requirements.insights.txt setup.py requirements/requirements.insights.in --upgrade
	pip-compile -o requirements/requirements.standalone.txt setup.py requirements/requirements.standalone.in --upgrade


# Repository management

.PHONY: changelog
changelog:        ## Build the changelog
	towncrier build

.PHONY: lint
lint:             ## Lint the code
	flake8 --config flake8.cfg

.PHONY: fmt
fmt:              ## Format the code using Darker
	@echo "Formatting code using darker, just like black, but only on changed regions of files."
	darker

# Container environment management

.PHONY: docker/prune
docker/prune:     ## Clean all development images and volumes
	@docker system prune --all --volumes

.PHONY: docker/build
docker/build:     ## Build all development images.
	./compose build

# e.g: make docker/test TEST=.api.test_api_ui_sync_config
# if TEST is not passed run all tests.
.PHONY: docker/test
docker/test:      ## Run unit tests.
	$(call exec_or_run, api, $(DJ_MANAGER), test, galaxy_ng.tests.unit$(TEST))

.PHONY: docker/loaddata
docker/loaddata:  ## Load initial data from fixtures
	./compose run --rm -e PULP_FIXTURE_DIRS='["/src/galaxy_ng/dev/automation-hub"]' \
 api manage loaddata initial_data.json

.PHONY: docker/migrate
docker/migrate:   ## Run django migrations
	$(call exec_or_run, api, $(DJ_MANAGER), migrate)

.PHONY: docker/resetdb
docker/resetdb:   ## Cleans database
	# Databases must be stopped to be able to reset them.
	./compose down
	./compose stop
	./compose run --rm api /bin/bash -c "./entrypoint.sh manage reset_db && django-admin migrate"

.PHONY: docker/translations
docker/translations:   ## Generate the translation messages
	./compose run --rm api bash -c "cd /app/galaxy_ng && django-admin makemessages --all"

.PHONY: docker/all
docker/all: 	                                ## Build, migrate, loaddata, translate and add test collections.
	make docker/build 
	make docker/migrate 
	make docker/loaddata 
	make docker/translations 

# Application management and debugging

# e.g: make api/get URL=/content/community/v3/collections/
.PHONY: api/get
api/get:          ## Make an api get request using 'httpie'
	# Makes 2 requests: One to get the token and another to request given URL
	http --version && (http :8002/api/automation-hub/$(URL) "Authorization: Token $$(http --session DEV_SESSION --auth admin:admin -v POST 'http://localhost:5001/api/automation-hub/v3/auth/token/' username=admin password=admin -b | jq -r '.token')" || echo "http error, check if api is running.") || echo "!!! this command requires httpie - please run 'pip install httpie'"

.PHONY: api/shell
api/shell:        ## Opens django management shell in api container
	$(call exec_or_run, api, $(DJ_MANAGER), shell_plus)

.PHONY: api/bash
api/bash:         ## Opens bash session in the api container
	$(call exec_or_run, api, /bin/bash)

.PHONY: api/runserver
api/runserver:    ## Runs api using django webserver for debugging
	# Stop all running containers if any
	./compose stop
	# Start only services if containers exists, else create the containers and start.
	./compose start worker content-app ui || ./compose up -d worker content-app ui
	# ensure API is not running
	./compose stop api
	# Run api using django runserver for debugging
	./compose run --service-ports --use-aliases --name api --rm api manage runserver 0.0.0.0:8000

.PHONY: api/routes
api/routes:       ## Prints all available routes
	$(call exec_or_run, api, $(DJ_MANAGER), show_urls)

.EXPORT_ALL_VARIABLES:
.ONESHELL:
.PHONY: api/create-test-collections
api/create-test-collections:   ## Creates a set of test collections
	@read -p "How many namespaces to create? : " NS; \
	read -p "Number of collections on each namespace? : " COLS; \
	read -p "Add a prefix? : " PREFIX; \
	ARGS="--prefix=$${PREFIX:-dev} --strategy=$${STRATEGY:-faux} --ns=$${NS:-6} --cols=$${COLS:-6}"; \
	echo "Creating test collections with args: $${ARGS}"; \
	export ARGS; \
	./compose exec api django-admin create-test-collections $${ARGS}

.PHONY: api/push-test-images
api/push-test-images:   ## Pushes a set of test container images
	docker login -u admin -p admin localhost:5001 || echo "!!! docker login failed, check if docker is running"
	for foo in postgres treafik mongo mariadb redis node mysql busybox alpine docker python hhtpd nginx memcached golang; do  docker pull $$foo; docker image tag $$foo localhost:5001/$$foo:latest; docker push localhost:5001/$$foo:latest; done

.PHONY: api/list-permissions
api/list-permissions:   ## List all permissions - CONTAINS=str
	$(call exec_or_run, api, $(DJ_MANAGER), shell -c 'from django.contrib.auth.models import Permission;from pprint import pprint;pprint([f"{perm.content_type.app_label}:{perm.codename}" for perm in Permission.objects.filter(name__icontains="$(CONTAINS)")])')

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
