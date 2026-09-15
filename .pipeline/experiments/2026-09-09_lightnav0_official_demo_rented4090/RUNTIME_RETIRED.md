# Runtime retired on 2026-09-10

Dr Sun requested removal of LightOrigins/LightNav model and runtime copies,
while retaining videos and results. The local checkpoint/work folders and the
rented4090 checkpoint/work/environment/tool folders were removed. This supersedes
historical instructions that assume those deployment paths still exist.

Historical reports, logs, configurations, raw observations, videos, and upstream
source provenance remain. The cleanup verified SHA-256 equality of every retained
regular file before and after deletion on each host.

Audit: [local cleanup](../2026-09-10_x_navdp_lite3_rented4090/setup/cleanup_local.json)
and [RTX 4090 cleanup](../2026-09-10_x_navdp_lite3_rented4090/setup/cleanup_rented4090.json).
The independent X-NavDP experiment retains identified Lite3 utility and asset
copies with their provenance; it does not depend on the deleted deployment.
