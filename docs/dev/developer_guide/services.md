# Pulp Services

## API

This application serves the REST API that the galaxy UI and CLI clients interact with on `/api/`.

## Workers

Pulp has a distributed tasking system that allows for longer running processes (such as content syncs) to run in the background without blocking API requests. Functions can be delegated to the tasking system by using the `dispatch()` function from `pulpcore.plugin.tasking`. Doing so will put the function call in a queue that will be picked up by the next available worker. Tasks can additionally lock certain resources in the database to prevent race conditions from happening.

The number of workers in a pulp system can be scaled up to whatever the needs of the system are.

## Content App

This is a file server where the software artifacts are served from. It's served from `/pulp/content/` on the API. Content in the content app is referenced via distributions. For collection `foo.bar:1.2.3` on a distribution with a base path of `my/distribution/base/path` would be served at `/pulp/content/my/distribution/base/path/foo-bar-1.2.3.tar`.
