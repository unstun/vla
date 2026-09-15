# Superseded setup attempts

These excerpts were captured from actual tool outputs before later retries.
They are not complete server log files.

- Initial PyPI download of decord 0.6.0 failed integrity checking. Expected
  SHA-256 `51997f20be8958e23b7c4061ba45d0efcd86bffd5fe81c695d0befee0d442976`,
  received `561e6b8b02a8c13ecbd0e4277c3a6169d887c13f4a2e7afada5026d372133262`.
  Pip rejected the package; normal retry succeeded. Hash verification was not
  disabled. `environment_retry.log` records the successful install and NF4 op.
- Pristine upstream import failed with `ModuleNotFoundError: No module named
  deepspeed` from `llava/train/sequence_parallel/globals.py:19`. Lazy imports in
  the work copy remove unused training/vision dependencies from single-GPU
  inference. No mock module or replacement neural output is used.
- Bulk rsync uploads repeatedly ended with `Connection to 23.252.106.36 closed
  by remote host`, `Broken pipe (32)` and exit 255/12. Bounded SSH writes with
  per-block and whole-file hashes completed the task-package transfer.
- The historical `gpu5070ti-relay` alias failed its current connection probe.
  The directly verified `gpu5070ti` alias was retained; host/GPU identity and
  the current experiment directory were checked before writes.
- HF snapshot transfer was slow. Its task-owned timeout/process was stopped;
  a resumable ranged downloader verifies Content-Range, byte counts and original
  HF LFS SHA-256 values. Initial and replacement download logs are retained.
