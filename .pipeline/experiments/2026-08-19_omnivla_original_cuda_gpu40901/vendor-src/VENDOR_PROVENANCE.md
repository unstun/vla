# Locally acquired Git dependencies

These source snapshots were acquired after gpu40901's direct GitHub clone made
no progress for five minutes. They preserve the exact upstream dependencies
declared by OmniVLA's `pyproject.toml`; only transport changes from a remote Git
clone to a hash-checked local source snapshot.

| Local directory | Upstream URL | Pinned commit | License evidence |
|---|---|---|---|
| `transformers-openvla-oft/` | `https://github.com/moojink/transformers-openvla-oft.git` | `bc339d9ad707454c0c115970db43c260067c61ab` | repository `LICENSE`, Apache-2.0 |
| `dlimp_openvla/` | `https://github.com/moojink/dlimp_openvla.git` | `040105d256bd28866cc6620621a3d5f7b6b91b46` | no license file found in the pinned snapshot |

Both commits were first resolved with `git ls-remote <official-url> HEAD`, then
checked out with shallow official GitHub clones. Git metadata is removed after
the commits are recorded so no pack file larger than 2 MiB remains in the local
experiment evidence. `SOURCE_MANIFEST.sha256` covers every retained source file.

The remote execution copy is
`/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/vendor-src/`.
The editable OmniVLA install is invoked with pip dependency substitution through
a task-owned constraints/install wrapper; these two sources are not edited.
