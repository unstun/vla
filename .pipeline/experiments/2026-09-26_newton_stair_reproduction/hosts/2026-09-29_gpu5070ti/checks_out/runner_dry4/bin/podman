#!/bin/bash
# Installed as `podman` first on PATH by checks/runner_dry4_tests.sh (port review round 4, N29): records the
# descriptors this podman process inherited, without forking, then runs the real podman.
fds=(/proc/$$/fd/*)
printf '%s :: %s\n' "${fds[*]##*/}" "$*" >> "$HOME/vla_exec/port/runner_dry4/podman_fds.txt"
exec /usr/bin/podman "$@"
