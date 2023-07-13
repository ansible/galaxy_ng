# galaxy_ng/m1

## Usage

This profile fixes a bug when running on M1 Macs where docker compose builds the pulp base image for x86
and then attempts to build any other images from the pulp base image for arm64, which is incompatible
with x86 base images.

This has to be a separate profile because the `platforms` arg in compose.yaml is not supported on older
versions of docker-compose or podman, that are used on x86 machines.
