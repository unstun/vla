# TIC-VLA DynaNav hospital trial on RTX 5070 Ti

The bounded closed-loop compatibility trial completed successfully on
2026-09-08. See [the result and its limits](RESULT.md),
[third-person video](runs/20260908T131741Z/third_person.mp4), and
[front-camera video](runs/20260908T131741Z/front_camera.mp4).

The local VLA repository is the source of truth. The execution copy is
`gpu5070ti:/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/`.
The source, assets, config, runtime and patch identities are recorded under
`manifests/`, `configs/`, `patches/` and `logs/`. Failed preliminary attempts
remain under `runs/` beside the successful `20260908T131741Z` run.

## Reproduction

1. Rebuild the small work copy with `scripts/prepare_workcopy.py` from the pinned
   upstream source listed in `manifests/source_files.txt`.
2. Run `scripts/download_assets.py EXPERIMENT_DIR`; it checks the exact official
   revisions, sizes and SHA-256 values in `manifests/official_assets.json`.
   `TICVLA_DOWNLOAD_WORKERS=4` enables bounded parallel range acquisition.
3. Configure task-owned paths in `configs/remote_env.sh`, verify the work manifest,
   and run `scripts/probe_model.py`, then `scripts/run_bounded.py` on the host.
4. `scripts/collect_run.py EXPERIMENT_DIR RUN_ID` records original benchmark output,
   audit traces, videos and a hashed original-camera archive.
5. Recover an interrupted large artifact with
   `scripts/fetch_remote_artifact.py EXPERIMENT_DIR RUN_ID ARTIFACT_NAME`.

Model/checkpoint bytes and the rebuildable work tree are path-specifically
ignored. The original camera archive is also path-specifically ignored and
covered by the run's artifact inventory. Videos, reports, raw text logs,
configuration and hash inventories remain visible in Git. A fresh simulation
produces a new run; it does not regenerate the exact historical observations.

The tested environment is Isaac Sim 5.1, with a local asset-loading workaround;
this is not the paper's full evaluation or a Lite3 integration result.
