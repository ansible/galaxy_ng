.SILENT:

# set the OCI_ENV_PATH to be ../oci_env/ if this isn't set in the user's environment
export OCI_ENV_PATH = $(shell if [ -n "$$OCI_ENV_PATH" ]; then echo "$$OCI_ENV_PATH"; else echo ${PWD}/../oci_env/; fi)


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

.PHONY: lint
lint:             ## Lint the code
	check-manifest
	flake8 --config flake8.cfg

.PHONY: fmt
fmt:              ## Format the code using Darker
	@echo "Formatting code using darker, just like black, but only on changed regions of files."
	darker

# Container environment management

.PHONY: docker/test/integration/container
docker/test/integration/container:      ## Run integration tests.
	docker build . -f dev/standalone/integration-test-dockerfile -t galaxy-integration-runner
	docker run -it --rm --add-host=localhost:host-gateway galaxy-integration-runner $(FLAGS)

.PHONY: oci-env/integration
oci-env/integration:
	oci-env exec bash /src/galaxy_ng/profiles/base/run_integration.sh $(FLAGS)

.PHONY: gh-action/ldap
gh-action/ldap:
	python3 dev/oci_env_integration/actions/ldap.py

.PHONY: gh-action/x_repo_search
gh-action/x_repo_search:
	python3 dev/oci_env_integration/actions/x_repo_search.py

.PHONY: gh-action/iqe_rbac
gh-action/iqe_rbac:
	python3 dev/oci_env_integration/actions/iqe_rbac.py

.PHONY: gh-action/keycloak
gh-action/keycloak:
	python3 dev/oci_env_integration/actions/keycloak.py

.PHONY: gh-action/rbac
gh-action/rbac:
	python3 dev/oci_env_integration/actions/rbac.py

.PHONY: gh-action/rbac-parallel
gh-action/rbac-parallel:
	python3 dev/oci_env_integration/actions/rbac-parallel.py $${RBAC_PARALLEL_GROUP}

.PHONY: gh-action/insights
gh-action/insights:
	python3 dev/oci_env_integration/actions/insights.py

.PHONY: gh-action/standalone
gh-action/standalone:
	python3 dev/oci_env_integration/actions/standalone.py

.PHONY: gh-action/community
gh-action/community:
	python3 dev/oci_env_integration/actions/community.py

.PHONY: gh-action/dab_jwt
gh-action/dab_jwt:
	python3 dev/oci_env_integration/actions/dab_jwt.py

.PHONY: gh-action/certified-sync
gh-action/certified-sync:
	python3 dev/oci_env_integration/actions/certified-sync.py

.PHONY: docker/db_snapshot
NAME ?= galaxy
docker/db_snapshot:   ## Snapshot database with optional NAME param. Example: make docker/db_snapshot NAME=my_special_backup
	docker exec galaxy_ng_postgres_1 pg_dump -U galaxy_ng -F c -b -f "/galaxy.backup" galaxy_ng
	mkdir -p db_snapshots/
	docker cp galaxy_ng_postgres_1:/galaxy.backup db_snapshots/$(NAME).backup

.PHONY: docker/db_restore
NAME ?= galaxy
docker/db_restore:   ## Restore database from a snapshot with optional NAME param. Example: make docker/db_restore NAME=my_special_backup
	docker cp db_snapshots/$(NAME).backup galaxy_ng_postgres_1:/galaxy.backup
	docker exec galaxy_ng_postgres_1 pg_restore --clean -U galaxy_ng -d galaxy_ng "/galaxy.backup"

# Application management and debugging

.PHONY: api/push-test-images
api/push-test-images:   ## Pushes a set of test container images
	docker login -u admin -p admin localhost:5001 || echo "!!! docker login failed, check if docker is running"
	for foo in postgres treafik mongo mariadb redis node mysql busybox alpine docker python hhtpd nginx memcached golang; do  docker pull $$foo; docker image tag $$foo localhost:5001/$$foo:latest; docker push localhost:5001/$$foo:latest; done

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

docs/install:
	@pip install -r doc_requirements.txt
	@pip install -U 'Jinja2==3.0.1'

docs/build:
	@mkdocs build --clean

docs/serve:
	@mkdocs serve

#########################################################
# Simple stack spinup ... please don't overengineer this
#########################################################

.PHONY: oci/standalone
oci/standalone:
	dev/oci_start standalone

.PHONY: oci/standalone/poll
oci/standalone/poll:
	dev/oci_poll standalone

.PHONY: oci/insights
oci/insights:
	dev/oci_start insights

.PHONY: oci/keycloak
oci/keycloak:
	dev/oci_start keycloak

.PHONY: oci/ldap
oci/ldap:
	dev/oci_start ldap

.PHONY: oci/community
oci/community:
	dev/oci_start community

.PHONY: oci/dab
oci/dab:
	dev/oci_start dab

.PHONY: oci/dab_jwt
oci/dab_jwt:
	dev/oci_start dab_jwt
