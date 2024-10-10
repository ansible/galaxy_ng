#!/usr/bin/env bash

if [ "$PULP_RESOURCE_SERVER_SYNC_ENABLED" = "true" ]; then
    pulpcore-manager task-scheduler --id dab_sync --interval 15 --path "galaxy_ng.app.tasks.resource_sync.run";
else
    echo 'Resource Sync is Disabled.';
fi
