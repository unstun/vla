# Continue the same post-reboot cohort

Stage: experiment + analysis. On 2026-10-12 Dr Sun paused the host-incident
investigation and requested continuation of the preceding navigation work.

Resume only attempts10–13 from the declared08–13cohort, on gpu5070ti. Existing
08 FINISHED and09 FAILED are immutable members of that same cohort. Preserve
the original request, progress, runner, protocol, returned audit and all prior
failures. The original pre-reboot cohort remains separate.

`resume_post_reboot.py` reuses the executed runner for the four unstarted tags,
writing a separate continuation root. Verify the original boot/source/native
identities, original prefix result hashes, and absent remaining output paths.
The wrapper may wait up to600seconds total for the original resource admission
conditions; no simulation is launched until they pass. Log every refusal and
never stop other jobs. Keep original per-run timeouts, fresh initialization,
original spatial start, full route, retention and navigation-failure handling.
Observe memory/swap/load at1Hz during the continuation as before.

Local source remains authoritative; sync only these new audit files and verify
their hashes. Large data and execution remain under `/data/sun/vla_mppi_20261009`.
Continuation root: `results/full_route_repeats_post_reboot_resume01_20261012`.
Control root: the same path with `_control` appended. No frozen navigation edits
or new version. Return compact hash-bound continuation results and report all
six outcomes together only after the actual six declared runs have closed.
An admission timeout leaves the original cohort incomplete, without consuming
an unstarted attempt or replacing any failure.

While the host is busy, inspect existing captures by streaming their archived
logs at low priority. Record observed failure triggers separately from native
same-input reproduction; do not treat symptom counts as a confirmed root cause.
