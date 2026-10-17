# v236 execution commands and evidence boundary

Activate the same private interpreter for Python shebang helpers before the
CPU wrapper: `export PATH=/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin:$PATH`.
Invoke its absolute Python with `cpu_launch.py preflight --attempt02`, then
`cpu_launch.py route --attempt01`. The actual completed preflight is02;
preflight01 failed before physics because the private bin was absent from PATH.
All preparation failures and runtime commands remain in diagnosis receipts.

User-level systemd cannot enforce a CPU quota on this host (only memory/pids
are delegated). Use the verified Docker4-CPU wrapper; retain the host library
layout and policy wheels. The source manifest remains frozen; runtime requests
record the complete environment/mount/command binding.

Exactly one new physical attempt was executed. Scanner regression and the245
actual scans pass; the route stops at35.59206771850586s on the unchanged evidence
writer queue bound. No subsequent physical run is authorized or performed.
