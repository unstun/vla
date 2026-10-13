# Restore boundary

Read STORAGE.json first. An upload-in-progress entry is not a remote verification.
The closed v100-v114 runtime/raw archive preserves successes, failures, the original
recorded scans, source/install/dependency files, test and build logs and the v111
failed/successful display attempts. No source roots are deleted during this repair.
The v115 video and compact rendering provenance are retained in the local repository;
its source physical states are in the v114 raw root.

Use the archive SHA256 and member_manifest.json hashes in STORAGE.json. Verify every
member before extracting into a fresh owned directory. Original runtime paths use
/private/tmp/vla_nav2_simrepair_5z7q27y7 mounted at /task and the local VLA repository
mounted read-only at /repo. Exact receipt entries rely on those container paths.
Do not merge an extraction into a different task's live runtime.

The execution image is sha256:d4aec648bd283fba07aa3a76724b53df69d3ee7a9ffbf08776bd835858729343.
It is retained locally, not included in the archive. Check its presence explicitly;
source/package receipts are not a claim that an absent image has been restored.
The source-only export entry is versions/v114/assemble_workspace.py, with the
frozen parent chain. Its build_export.sh requires the recorded Foxy ARM64 dependencies.

To continue current execution use the preserved local runtime and frozen v114
source/runtime receipt. Any code/config change needs the next unused integer
version (v115 is display-only and frozen), new checks and a new physical run.
Do not relabel the single successful run as continuous30Hz or repeatable navigation.
Jetson startup is still pending user-provided access; no actuation is authorized.
