---
tags:
  - on-premise
  - tech preview
---

# Galaxy NG Installation

The Galaxy Dev Team doesn't maintain any public image or installation process, however there is
an example on how to run galaxy using docker compose:

```console
$ git clone https://github.com/ansible/galaxy_ng
$ cd galaxy_ng
$ docker compose -f dev/compose/standalone.yaml up
```

The UI is hosted and maintained on a separate repository and instructions to execute it are
available on: [ansible-hub-ui](https://github.com/ansible/ansible-hub-ui)

Galaxy NG is a [Pulp plugin](https://pulpproject.org/pulpcore/docs/admin/learn/architecture/). As a plugin, Galaxy_NG has multiple installation methods available.
Further information can be found on [Pulp Docs](https://pulpproject.org/pulpcore/docs/user/tutorials/)
