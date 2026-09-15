# Deployment design

Import the clean NaVILA commit into the dated upstream directory and preserve it
unchanged. Keep compatibility edits in a separate execution copy, with a patch
record. Reuse the existing CUDA 12.8 Torch installation through a task-local
venv; do not change the Isaac environment. Use isolated Transformers 4.37.2
initially and a Blackwell-capable bitsandbytes wheel. Attention may use SDPA.

The language backbone uses NF4 with double quantization and FP16 compute;
the vision tower and projector remain FP16. The input is eight RGB frames
(upstream padding/history logic), plus a verbatim user instruction in the
upstream navigation wrapper. The output is retained text, not motor commands.
Use recorded simulation RGB with origin/hash metadata; repeat identical input
and vary language. CPU offload, output parsing, and frame duplication must be
explicit. Network downloads are bounded separately from inference.

Original weights are available at a pinned public HF revision; retain their
verified hashes. Keep exported NF4 weights locally and record regeneration
instructions, rather than retaining two large copies on the Mac's limited disk.
