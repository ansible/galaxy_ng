#!/bin/bash

CONTAINERS="galaxy_ng_api_1 galaxy_ng_worker_1"

for CONTAINER in $CONTAINERS; do
    echo $CONTAINER
    docker exec -u root -it $CONTAINER /bin/bash -c 'kill -HUP 1'
    docker exec -u root -it $CONTAINER /bin/bash -c 'kill 1'
done

rm -rf /tmp/coverage_results
mkdir -p /tmp/coverage_results/data
cp dev/standalone/.coverage* /tmp/coverage_results/data/.
cd /tmp/coverage_results

coverage combine data
coverage report -i
