# Evidence restoration

The local frozen version chain and source exports are authoritative. The archive
contains execution copies, all successful/failed component attempts, normal and
fault mapping replays, original Newton v92-v98 attempts, raw sensor/telemetry
archives and exact build/install bytes. It does not contain a successful robot run.

- Remote object: `gpu5070ti:/home/sun/vla_artifacts/2026-10-08_nav2_full/attempt01/vla_nav2_full_evidence_20261008.tar.gz`.
- Archive bytes: 425237207.
- SHA-256: `fbf2b343353646e15b02f33d7d9482fc30ae9e8ff198ddfe9340f6dd9e8fe022`.
- Expanded regular-file bytes: 1111168445 across 20689
  regular-file/symlink entries. `MEMBER_MANIFEST.json` records each byte digest
  or symlink target. Directory metadata is not a navigation input.
- Check `STORAGE.json` for completed transfer/member verification and cleanup.

Restore into a new, empty temporary directory. Verify the archive digest before
extracting and verify restored members against `MEMBER_MANIFEST.json`. Do not
replace the VLA source tree with an archived execution workspace.

The root `vla_nav2_full_qbrlg8yi/portable_v99` is the clean source/build/test export.
The `vla_newton_vNN_*/runs/vNN_mac_trial01_attempt01` roots preserve every physical
attempt, including `raw_capture.zip` when managed retention packed raw files.
v98 has different final Linux state and last-ack bytes; retain both and its
failed `state_copyback.json`. Never overwrite one with the other to make it pass.

To regenerate the source workspace without restoring runtime binaries, use
`versions/v99/assemble_workspace.py` from this experiment and follow
`.pipeline/design/2026-10-08_nav2_foxy/DEPLOYMENT.md`. Rebuild for the target OS and
architecture. The original 188-scan input is separately pinned by the v87/v91
receipts and its previously verified upstream evidence archive.

For investigating the Mac physical failure, frozen v98 records the original
`run_mac_corner.py`, runtime receipt, scene/policy/input identities and 90 s bound.
The archive preserves installed workspace bytes, but does not contain a Docker
image export. The disposable image is removed after retention; its recorded ID
is provenance, not a promise that a rebuilt image has the same digest. If that
exact image is unavailable, qualify a newly built environment and bind a new
version/receipt before another physical run. Do not edit v98's frozen receipt or
claim an exact-environment rerun from different image bytes. No real-robot motion
authorization follows from these simulation instructions.
