# v154 transport qualification metadata correction

Stage: experiment + analysis. Host parent v153, native v151 unchanged.
v153attempt01was rejected by the launcher before physics because quality.json
omitted native_packages_available. Retain that failed launch; do not count it
as a physical navigation trial. v154records the actual14packages and38tests
from the same already-pinned ARM64 receipt. Transport behavior,100msper-request
timeouts, bounded exact-byte retries and every native contract are unchanged.

Require inherited host/transport tests and graph checks, plus metadata admission
regression against the actual launcher's required package field. Freeze before
an original-start physical trial. This is not a navigation repair claim.

Recovery execution also requires a refreshed native install receipt after the
old temporary workspace disappeared. Source and image stay identical; the
rebuild and38tests must finish before the graph/physics gates. Archive the
closed rebuilt environment before further physical execution.
