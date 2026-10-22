# Design

Remove hook configuration and all three host hook directories. Claude settings
retain their environment and plugin map. Skill and agent discovery remains;
the installed agent instructions already support reading task/context files
when no hook marker is present. Session identity comes from the native runtime
or TRELLIS_CONTEXT_ID, not a shell hook.

The shared task CLI must follow the configured inline execution preference
when applying the empty-context gate. Merely retaining another host's directory
does not imply delegation. The existing auto mode and explicit override remain.

Finalize the 45 reviewed framework paths, except removed hook sources, with
the smallest task.py fix. Preserve other upstream template bytes and the
upstream hash registry; document the intentional local patch in the harness
spec. Keep the five research/retention paths out of the commit.

Recovery archive stores exact pre-removal Python sources outside discovery
paths. Compile/test only temporary fixtures, and verify the published tree.
