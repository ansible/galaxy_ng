#!/bin/bash

./build.sh

rm -rfv ../galaxy_pulp
mv ./galaxy-pulp/galaxy_pulp ../galaxy_pulp
