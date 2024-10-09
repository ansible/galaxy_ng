# Dev Binary Tools

## Reloader

A Script that splits `DEV_SOURCE_PATH` variable and list all files on its directories,
then omit some unwanted files watching for `.py|yaml` only for changes.

Then it calls `entr` to reload the passed command.

## entr

A tool to watch files for changes and reload
This file is compiled specifically for the container in use.

LINK: https://eradman.com/entrproject/

In case recompilation is needed, run inside the container.

```bash
# Install entr so we can have reload on worker processes
# the checkout is to fix a compilation error caused by this commit
# https://github.com/eradman/entr/commit/f9ac92d17e42236fe6b5e8492e087620173c7b24
RUN git clone https://github.com/eradman/entr && \
    cd entr && \
    git checkout 0d2d92d6052624a1e03a2a654e98e1c49f9955d9 && \
    cp Makefile.linux Makefile && \
    make
```

Then copy the generated `entr` binary.

## devinstall

Install all paths listed on `DEV_SOURCE_PATH` as editable every time the compose starts.

## wait

Wait until a file is present on the shared volumes,

```console
$ wait /etc/pulp/certs/filename;
Waiting for /etc/pulp/certs/filename ...
# sleep 2 secs
Waiting for /etc/pulp/certs/filename ...
# sleep 2 secs
Waiting for /etc/pulp/certs/filename ...
...
```
