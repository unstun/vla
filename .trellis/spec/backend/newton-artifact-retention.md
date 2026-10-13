# Newton artifact retention

Applies to new recordings, recorded-state rendering and closed-run maintenance.
Implementation: `versions/v51/` in the 2026-09-26 Newton experiment.

## Storage location and returns (2026-10-01)

Dr Sun requested that most heavy files remain on gpu5070ti. Follow the repository
`AGENTS.md` artifact-storage policy instead of older full-data return defaults.
This changes storage/return planning, not the frozen v51 implementation.

Keep full captures, NPZ, state/backend JSONL, verbose logs, portable archives,
models and build/runtime environments on gpu5070ti. Perform full-data analysis
and MP4 rendering there by default. Locally retain source/configuration,
compact results, plots, hash manifests and only the finished videos needed for
review. ZIP files are bulk too; compression is not a reason to download them.
Use an explicit transfer allowlist with a checked aggregate byte count, never a
recursive return of the full run or experiment tree.

Before starting a new run, declare the remote artifact root, local return list
and expected local bytes in its execution plan. Save a compact local remote
artifact record containing run/version, host, absolute paths, sizes, SHA-256,
verification time and retrieval/reanalysis commands. A checksummed per-file
manifest may describe a directory/archive. Bind returned summaries and video
provenance to those hashes; retain the full inputs on the remote host.

Run original full-evidence validators against the remote data and return their
results. A legacy validator requiring expanded local data has not passed merely
because a locator exists. Record remote validation separately; adapt a future
validator in a new version if necessary. No Linux v51 rendering qualification is
implied by this storage policy. If remote rendering is unavailable, report the
limitation before arranging a bounded local-data exception.

Existing local bulk is eligible for removal only after closed-run checks,
byte-identity verification of its durable remote copy and saving a local
retrieval record. Preserve required source fixtures and frozen version bytes.
This policy update itself neither migrates nor deletes historical artifacts.

## Recording, rendering and closed-run retention

Use `scripts/run_managed.py` for new bounded runs/renders, passing the original
child command and preserving its normal version/build gates. Do not nest a
launcher that creates the same run directory. Frozen historical launchers remain
unchanged; when reproducing one directly, run the declared closed-output
retention step afterward. Never silently rewrite frozen source to adopt storage
policy. The navigation reference is independent of the artifact-pipeline version.

Render directly to MP4 with the v51 renderer. Keep three representative PNGs and
frame provenance by default; full PNG sequences require explicit debugging
intent. Validate full decode, count, fps and original state identity. Display30FPS
does not establish planner30Hz, RTF1 or navigation acceptance. Raw recordings may
include an untimed startup prefix: omit it from a wall-time navigation display,
preserve its original records and reject missing timestamps inside navigation.

Closed-log compression must preserve original bytes and hashes. For portable
archives, verify every member before removing expanded files; keep external
member paths/hashes, archive identity, original metadata and a restore command.
NPZ is already compressed: archive it for consolidation, not an assumed large
compression gain. Never discard unique failure evidence or a source fixture.
Legacy readers may need restoration; do not claim their expanded paths still
exist. New readers may stream verified archive members.

Cleanup requires completed application/supervisor evidence, no active marker or
writer and unchanged file identities. Uncertain state, metadata mismatch,
corrupt/incomplete video or insufficient temporary space must retain originals.
An interrupted manager leaves its active marker for inspection. Preserve child
failure status even if its archive succeeds. Disk-space preflight is not a quota
or permission to change a running planner's stop behavior.

Use exact run-path ignores with repo-visible SHA/provenance/restoration records
for large local archives. Separate logical sizes, allocated-file savings and
current filesystem free space. Tests and measured maintenance results are in
`versions/v51/RESULTS.md`; do not infer success solely from compressor exit code.

For timing plots, map wall time to simulation time with recorded timestamp
pairs. Do not label the navigation pacing anchor as simulation zero when it
follows factory startup. Show the untimed prefix separately, retain failed and
paused intervals, and distinguish a threshold-filtered pause count from the
absolute longest pause. If remote plotting libraries are absent, compute and
verify data remotely, then return only compact tables for local plotting. Pin
the executed analysis source separately from later display-only edits. v57's
`analysis/verification.json` and `analysis/plot_provenance.json` demonstrate this
split; a directory named `matplotlib` may contain only a font cache.

## Explicit Mac execution exception and clock domains (2026-10-04)

Dr Sun explicitly authorized Newton tests on Mac while gpu5070ti was busy. For this bounded exception, place build/install/raw captures/archives at a unique private/tmp root outside repo; return compact source/config/report/plots/locators and preserve unique raw until reviewed durable transfer. Remove owned containers and temporary build bytes after validation. Never describe temporary Mac captures as remotely stored. Original retention must run after all native ros2-run descendants close their writers; graph-wrapper exit alone is insufficient.

Pre-created empty tmpfs parents cross three admission checks: managed run, bounded supervisor and episode storage. All three must accept only verified empty owned directories and reject existing data. Test the actual manager->supervisor->child->retention chain plus the actual episode-storage helper. Verify real qualification keys and installed-source receipts before source freeze. Once frozen, host fixes use a new integer package; restore a raced current file only from its unchanged original snapshot and preserve alternate bytes/failure evidence.

Mac physics pacing and Linux native planner/controller events use different monotonic origins. Map recorded converged clock offsets before selecting windows; then map actual wall/physics timestamp pairs for plotting. A30Hz raw controller cannot establish matching backend heartbeat delivery or successful planner30Hz. In these two shortened runs, original heartbeat stopping completes and both requested90s/late70s acceptance remain untested. Preserve process/retention success separately from FAILED navigation.

## Corner-local capture and interruption boundary (2026-10-04)

An explicit corner fixture may omit route-prefix traversal while retaining the
original final goal and full scene. Record the measured pose witness, triangle-ray
spawn screen and actual factory handoff; state that policy/map/planner caches
are fresh unless a real state restore is verified. Identical spawn/handoff does
not make independently evolving planner trajectories a same-input comparison.

Closed physical captures must be remotely archived and every file hash/size
verified before starting review rendering. Archive render outputs before local
cleanup. An ACK failure or absent final result still permits a labeled actual
partial video; it does not permit synthesizing final results or reporting
verified state copyback/stop. Display/storage success and physical failure are
separate results. Preserve earlier interrupted attempts and disclose unavailable
temporary raw roots rather than relabeling them as remotely archived.

v76/v77 provide executable closeout examples. Their videos use original causal
indices/times and zero physics, with three visual samples and full decode.
The upstream last saved gate is open despite stationary motion; do not infer
heartbeat_stale or completed hold/quiescence merely from a stationary video.
