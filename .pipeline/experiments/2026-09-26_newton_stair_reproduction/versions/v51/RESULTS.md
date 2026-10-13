# v51: simulation artifact storage repaired

Storage/rendering work, 2026-10-01. Navigation reference remains v48. v51 derives
its display renderer from v46 and changes no planner, controller, sensing rate,
trajectory, dynamics or stop protocol. No new physics trial was run.

## Why disk usage grew

The renderer encoded MP4s but kept the complete PNG sequence afterward. Existing
runs contained62,708 PNGs, about23.235 GB. JSONL contributed17.167 GB because the
worker repeatedly records full backend snapshots, including growing histories,
and verbose telemetry. There were48,993 NPZ files totaling12.174 GB; those sensor
captures were already compressed. Creating separate prepared video `view` runs
also duplicated some large logs. The renderer then loaded whole backend logs
into memory even though it only drew job/terminal status.

At the initial audit this experiment occupied about61 GiB, including52 GiB of
runs. The host reported **948 MiB free**. After maintenance it reports about
**27 GiB free**. The host remains shared with other disk activity; allocated-file
savings and filesystem free-space changes are separate measurements.

## Existing data reclaimed and preserved

| Action | Verified result | Allocated-file reduction |
|---|---:|---:|
| Remove redundant PNG intermediates | **62,371 frames across46 completed renders** | 23.215 GB |
| Transparent compression of closed logs | **152 files**, original paths/content hashes preserved | 9.237 GB |
| Lossless archives of failed/diagnostic captures | **10,260 members across3 runs** | Additional1.121 GB |

File-allocation accounting totals about**33.57 GB (31.27 GiB)** of reduction.
Do not equate this sum directly to APFS free space. The verified current counters
and filesystem reading are in [verified_summary.json](../../audits/2026-10-01_artifact_storage/verified_summary.json).

Every pruned sequence passed original video SHA-256, source-state SHA-256,
individual PNG SHA-256, frame count/fps and complete MP4 decoding. All MP4s,
original frame manifests and source states remain, together with three exact
PNG previews per render. Six incomplete render directories were retained because
their final video evidence was absent; the largest is about112 MB. Metadata
preservation failures in log compression also retain the originals.

Archives remain in their original run directories:

| Run | Original members preserved | ZIP size |
|---|---:|---:|
| `v49_realtime_trial02` | 794 | 176.3 MB |
| `diag_v31_clock03` | 5,670 | 1,503.6 MB |
| `diag_v31_clock04` | 3,796 | 996.6 MB |

NPZ members are stored without redundant recompression; large text uses ZIP LZMA.
All members were reread and hashed before removing expanded files. The original
v49 return manifest's **909 files remain verifiable**, through either their
original paths or the verified archive. Each archive has an external member
manifest, SHA-256, original metadata and restore instructions. See
[LOCAL_ONLY_BYTES.json](LOCAL_ONLY_BYTES.json); only these three exact large
archive paths were added to `.gitignore`. No repository-wide extension ignore.

**Legacy readers that require archived NPZ/JSONL paths must restore first.**
This is a storage relocation, not deletion of failure evidence. The new display
reader accesses archived text directly. The three selected archive receipts and
all maintenance operations are recorded separately from frozen version records.

## Prevention in future runs

- New bounded work uses `scripts/run_managed.py`. It checks a4 GiB free-space
  reserve before launching and runs retention only after the supervisor exits.
  Explicit process/terminal failures are archived automatically. Successful
  macOS runs preserve paths through transparent compression; portable archival
  is available explicitly and is used on other platforms. The reserve is a
  preflight check, not a quota for arbitrarily long captures.
- The v51 renderer streams RGB frames directly to FFmpeg. Default output is
  an MP4, frame provenance and three preview PNGs. Full PNG retention requires
  `--keep-frames`. Partial failures retain their partial video/provenance and
  are not marked successful. Rendering also checks free space and a512 MiB
  encoded-video limit.
- Backend JSONL is consumed incrementally, retaining only display status in
  memory. Raw recorded episodes can be rendered directly; no duplicate view
  run is needed. Untimed factory-startup prefixes are omitted from this
  initialized-navigation display, while all original startup records remain.
  Missing timestamps inside navigation are rejected, not fabricated.
- Runtime capture rates and schemas remain unchanged, so this maintenance does
  not alter the v48/v50 timing experiment. Most storage reduction occurs after
  capture. Frozen historical launchers intentionally remain unchanged and do
  not automatically gain this policy; use the new managed entry for future work.

Commands and restoration details: [README.md](README.md).

## Direct validation

**21 focused tests pass**: complete/corrupt/incomplete videos, frame/source identity,
active files, symlinks, transparent-compression byte/metadata preservation, archive
round-trip and corruption, failure before pruning, refusal to overwrite changed
restored files, failed versus running supervisor evidence, interrupted encoder,
explicit debug frames, and causal timestamp handling.

- `v51_stream_smoke02`:60 actual recorded v45 frames,30 FPS, full decode,
  three preview PNGs, zero physics steps. The first full-resolution RGB frame
  exactly equals the preserved v46 reference image.
- `v51_stream_smoke04`:60 frames directly from the original v50 capture, using
  the managed entry, original wall timestamps and measured timing metadata.
  Full decode and automatic retention pass; three preview PNGs, zero physics.
- `v51_retention_smoke02`: a synthetic failed child retains exit code7 after
  automatic verified archival. The oversized free-space requirement refuses
  a synthetic launch before creating its run directory.
- Recheck of v50's6,611 current source files and6,611 frozen snapshot files,
  v48's6,442 source files, and all6,966 preserved v49 version-directory files
  passes. Navigation source and frozen failure records are untouched.
- [verify_storage.py](verify_storage.py) rechecks all compressed-log hashes,
  preserved video/state/preview identities, archive members and the original
  v49 return manifest. [Integration checks](integration_checks.json) and
  [test output](tests_final.log) are retained.

Earlier attempts remain visible: smoke01 could not access the Mac graphics
service inside the sandbox; smoke02 succeeded with the same renderer through
the authorized graphics environment. Smoke03 exposed the untimed factory prefix
in raw v50 captures; that case is now explicitly handled and covered by tests.
No failed attempt was renamed into a success. Linux managed-run integration and
a new physics run were not performed or claimed.
