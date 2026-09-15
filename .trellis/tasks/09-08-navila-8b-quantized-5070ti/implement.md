# Execution and verification

1. Inspect upstream four-bit loading, prompt, preprocessing and dependencies.
2. Download the pinned checkpoint and verify LFS SHA-256 identities.
3. Prepare an isolated environment and test a real NF4 CUDA operation.
4. Sync source/scripts/fixtures; verify the manifest; load the full VLA.
5. Run bounded recorded-image navigation probes and inspect raw outputs.
6. Export and reload NF4 weights; sync evidence and weights to the local project.
7. Report deployed inference separately from untested closed-loop navigation.

Record all failures and local compatibility patches. No compute-helper is
available in this checkout or PATH; use explicit rsync + SSH with the same
local-before-remote and sync-back contracts.

## Execution outcome

NF4 inference, 11 recorded-image cases, deterministic repeat, export and fresh
process reload passed. CUDA layer/state/device checks confirm actual four-bit
language inference. Local validation checked 24 + 13 artifact hashes. See the
experiment RESULT.md for measured resources and raw language differences.

Code, inputs and evidence are local; the derived 6.64 GB model payload currently
remains on the GPU host. Full payload mirroring to the Mac is not complete; a
4 MiB SSH download probe took 17.53 s. Preserve this distinction rather than
claiming every planned byte was delivered. Original public weights, derived
hashes and regeneration commands are recorded. No closed-loop simulation ran.
