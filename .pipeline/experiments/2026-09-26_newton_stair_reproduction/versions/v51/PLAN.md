# v51: bounded artifact storage, display and post-run maintenance only

Authorized by Dr Sun on 2026-10-01: reduce simulation disk growth, compile videos
instead of retaining PNG sequences, and compact failed diagnostic outputs.
Stage: experiment + analysis. Inline execution; no Trellis task by prior choice.

## Scope before editing

The existing renderer saves every PNG, compiles an MP4, then retains both.
Recorded backend snapshots repeat growing history. All sensor NPZ files are
already compressed. At audit, this experiment uses about61 GiB, its runs52 GiB,
and the host has under1 GiB free. Runs contain23.235 GB PNG and17.167 GB JSONL.

Add storage-only v51 tools and a renderer derived from frozen display-only v46.
Keep v46's recorded wall timeline and rendering behavior. Replace frame-file
spooling with a bounded FFmpeg stream, keep per-frame provenance and a few preview
images, fully decode/count the MP4 before acceptance, and expose PNG retention
only as an explicit debugging option. Preserve failed partial video/provenance.

Provide closed-run maintenance: verify existing video identity, source state,
frame hashes/count and full decode before pruning redundant derived PNGs. Keep
original frame manifests, representative frames, MP4s and pruning receipts.
Compact large closed logs losslessly; retain raw sensor NPZ evidence. Support
portable ZIP archival/restoration with per-member hashes for failed-run captures,
and verify before removing an expanded archive member. Never touch an active
run, unique video, model, source snapshot or unrelated project. Do not change
frozen v3-v50 source bytes or old manifests. Original hashes remain authoritative.

Expected new files: artifact maintenance/verification CLI, streaming video sink,
v51 renderer/heading wrapper, post-run wrapper, focused failure-path tests,
usage/results and operation journals. Existing experiment indexes/specs gain
only storage guidance. The navigation reference remains v48; v51 does not
inherit/promote v50 navigation, run physics, change planner logs or stop behavior.

Validation: reject incomplete/corrupt/mismatched videos without pruning; verify
streamed output and frame count with FFmpeg; archive round-trip exact bytes and
hashes; refuse changed/active/symlink inputs; verify frozen source identities;
report measured allocated and filesystem space before/after. Render a bounded
recorded-state smoke if the existing local runtime is available. No new physics.
