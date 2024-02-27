#!/bin/bash

set -e

docker-killall
docker-rmall

ANSIBLE="ansible-playbook -i 'localhost,' --forks=1 -vvvv"

$ANSIBLE build_container.yaml
$ANSIBLE start_container.yaml
$ANSIBLE run_unit_tests.yaml
