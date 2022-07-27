#!/bin/bash

# Dump a readable list of the environment variables for the
# api container's first pid, as stored in /proc on the host.

CONTAINER_PID=$(docker inspect galaxy_ng_api_1  | jq '.[0].State.Pid')
sudo cat /proc/$CONTAINER_PID/environ | tr '\0' '\n' | sort

