.SILENT:

.DEFAULT:
.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -F "##" Makefile | grep -F -v grep -F | sed 's/^/\n/' | sed 's/#/\n/'

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

.PHONY: lint
lint:             ## Lint the code
	check-manifest
	flake8 --config flake8.cfg
	ruff check .

.PHONY: fmt
fmt:              ## Format the code using Darker
	@echo "Formatting code using darker, just like black, but only on changed regions of files."
	darker

# Version / bumpversion management

.PHONY: dev/bumpversion-patch
dev/bumpversion-patch:  ## 'bumpversion path' to go from 4.1.0 -> 4.1.1
	bump-my-version bump --verbose patch

.PHONY: bumpversion-minor
dev/bumpversion-minor:  ## 'bumpversion minor' to go from 4.1.1 -> 4.2.0
	bump-my-version bump --verbose minor

.PHONY: bumpversion-major
dev/bumpversion-major:  ## 'bumpversion major' to go from 4.2.9 -> 5.0.0
	bump-my-version bump --verbose major

.PHONY: dev/bumpversion-build
dev/bumpversion-build:  ## 'bumpversion build' to go from 5.3.7.a1 -> 5.3.7.a2
	bump-my-version bump --verbose build

# another 'bumpversion release' to from from 5.3.7.b1 -> 5.3.7
.PHONY: dev/bumpversion-release
dev/bumpversion-release:  ## 'bumpversion release' to from 5.3.7.a1 -> 5.3.7.b1
	bump-my-version bump --verbose release

# Documentation Management

.PHONY: docs/clean
docs/clean:  ## Clean the documentation
	@rm -rf site

.PHONY: docs/install
docs/install:   ## Install the documentation dependencies
	@pip install -r doc_requirements.txt
	@pip install -U 'Jinja2==3.0.1'

.PHONY: docs/build
docs/build:  ## Build the documentation
	@mkdocs build --clean

.PHONY: docs/serve
docs/serve:  ## Serve the documentation
	@mkdocs serve


# Docker Compose Environment Management

.PHONY: compose/standalone
compose/standalone:  ## Spin up a standalone stack
	docker compose -f dev/compose/standalone.yaml up

.PHONY: compose/standalone/down
compose/standalone/down:  ## Stop a standalone stack
	docker compose -f dev/compose/standalone.yaml down

.PHONY: compose/insights
compose/insights:  ## Spin up a insights stack
	docker compose -f dev/compose/insights.yaml up

.PHONY: compose/insights/down
compose/insights/down:  ## Stop a insights stack
	docker compose -f dev/compose/insights.yaml down

.PHONY: compose/aap
compose/aap:  ## Spin up AAP stack
	docker compose -f dev/compose/aap.yaml up

.PHONY: compose/aap/down
compose/aap/down:  ## Stop AAP stack
	docker compose -f dev/compose/aap.yaml down

.PHONY: compose/community
compose/community:  ## Spin up a community stack
	docker compose -f dev/compose/community.yaml up

.PHONY: compose/community/down
compose/community/down:  ## Stop a community stack
	docker compose -f dev/compose/community.yaml down

.PHONY: compose/certified
compose/certified:  ## Spin up a certified stack
	docker compose -f dev/compose/certified-sync.yaml up

.PHONY: compose/certified/down
compose/certified/down:  ## Stop a certified stack
	docker compose -f dev/compose/certified-sync.yaml down

# Dev Environment Utils

.PHONY: compose/db_snapshot
NAME ?= galaxy
compose/db_snapshot:   ## Snapshot database with optional NAME param. Example: make docker/db_snapshot NAME=my_special_backup
	docker exec compose-postgres-1 pg_dump -U galaxy_ng -F c -b -f "/galaxy.backup" galaxy_ng
	mkdir -p db_snapshots/
	docker cp compose-postgres-1:/galaxy.backup db_snapshots/$(NAME).backup

.PHONY: compose/db_restore
NAME ?= galaxy
compose/db_restore:   ## Restore database from a snapshot with optional NAME param. Example: make docker/db_restore NAME=my_special_backup
	docker cp db_snapshots/$(NAME).backup compose-postgres-1:/galaxy.backup
	docker exec compose-postgres-1 pg_restore --clean -U galaxy_ng -d galaxy_ng "/galaxy.backup"

.PHONY: compose/db_shell
compose/db_shell:   ## Open a shell in the database container
	docker exec -it compose-postgres-1 psql -U galaxy_ng galaxy_ng

.PHONY: compose/dj_shell
compose/dj_shell:   ## Open a shell in the django container
	docker exec -it compose-manager-1 django-admin shell_plus

.PHONY: compose/dj_show_urls
compose/dj_show_urls:   ## Show the urls registered in Django
	docker exec compose-manager-1 django-admin show_urls

.PHONY: compose/dynaconf/inspect
compose/dynaconf/inspect:   ## Inspect the dynaconf configuration
	docker exec compose-manager-1 dynaconf inspect -m debug -vv --format yaml

# Test data population

.PHONY: push-test-images
push-test-images:   ## Pushes a set of test container images
	docker login -u admin -p admin localhost:5001 || echo "!!! docker login failed, check if docker is running"
	for foo in postgres treafik mongo mariadb redis node mysql busybox alpine docker python hhtpd nginx memcached golang; do  docker pull $$foo; docker image tag $$foo localhost:5001/$$foo:latest; docker push localhost:5001/$$foo:latest; done

# Local execution of tests

.PHONY: test/unit
test/unit:  ## Run unit tests
	# if tox is not found raise a warning and install it
	@which tox || (echo "tox not found, installing it now" && pip install tox)
	tox -e py311

.PHONY: test/integration/standalone
test/integration/standalone:  ## Run integration tests
	# if pytest is not found raise a warning and install it
	@which pytest || (echo "pytest not found, installing it now" && pip install -r integration_requirements.txt)
	@echo "Running integration tests"
	HUB_ADMIN_PASS=admin \
	HUB_API_ROOT=http://localhost:5001/api/galaxy/ \
	GALAXYKIT_SLEEP_SECONDS_POLLING=.5 \
    GALAXYKIT_SLEEP_SECONDS_ONETIME=.5 \
    GALAXYKIT_POLLING_MAX_ATTEMPTS=50 \
    GALAXY_SLEEP_SECONDS_POLLING=.5 \
    GALAXY_SLEEP_SECONDS_ONETIME=.5 \
    GALAXY_POLLING_MAX_ATTEMPTS=50 \
	pytest  galaxy_ng/tests/integration \
	-p 'no:pulpcore' -p 'no:pulp_ansible' \
	-v -r sx --color=yes -m 'deployment_standalone or all'
