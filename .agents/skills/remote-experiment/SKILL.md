---
name: remote-experiment
description: Run and diagnose authorized VLA work on remote hosts, synchronize local source and return reproducible results. Use for remote execution, not ordinary local edits.
---

# Remote Experiment Execution

The local VLA repository is the source of truth; remote workspaces are execution
copies. Read the relevant task and recorded host/run configuration. Resolve the
actual SSH alias, destination and environment from available configuration;
do not assume a compute-helper service or inherit a host from another project.

Before execution, state the exact source revision or task-owned diff, sync
paths, command/configuration and expected outputs. Verify the destination and
available resources. Use the existing project runner or transfer commands;
`compute-helper` is optional when it is actually installed and configured.

For authorized work: edit locally, synchronize the selected paths, execute,
inspect raw output, fix ordinary in-scope failures and repeat the appropriate
check. Temporary remote edits must return to the same local paths. A bounded
smoke does not authorize formal training or a longer experiment.

Record run ID, host/workspace, source identity, command, environment and output
locations. Return compact reports, logs needed to interpret results, hashes and
review videos locally; keep heavy bytes on gpu5070ti with storage/recovery
provenance. Verify returned artifacts before claiming completion.

Separate source changes, import checks, runtime smoke, formal runs and accepted
results. Formal training, long remote runs, destructive operations and robot
actuation require Dr Sun's explicit authorization. Reuse existing authorization
within its scope rather than asking again for each routine command.
