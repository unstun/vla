# NaVILA 8B NF4 deployment probe

Status: NF4 CUDA inference and export/reload passed; see [RESULT.md](RESULT.md).
This is pretrained, open-loop inference, not a navigation success test. User
selected quantized NaVILA deployment on 2026-09-08. Evidence is verified locally;
the 6.64 GB derived NF4 payload remains on the GPU execution host.

Pristine source: `references/upstream/2026-09-08_navila_quantization/source/NaVILA`,
commit `76b98f233dd0fff05dfcd69435eec6740febff9d`. Original model:
`a8cheng/navila-llama3-8b-8f`, revision
`b2294e96581454468d6b94f38201f4f965ef48b7`.

The upstream builder supports bitsandbytes NF4. This experiment uses that route,
with FP16 vision/projector and language compute. The paper used AWQ W4A16;
its 8.6 GB measurement is not a measurement of this deployment.

Local source/configuration/evidence live in this directory. Remote execution
copy: `/home/sun/vla_exec/2026-09-08_navila_8b_quantized_5070ti` on `gpu5070ti`.
The task-local venv inherits read-only Torch 2.7.0+cu128 from the existing Isaac
environment and overlays task-specific packages. Inference is bounded to 600 s.

Regenerate original weights with `python scripts/download_assets.py EXPERIMENT`;
`setup/original_weight_manifest.json` records hashes checked against HF LFS.
`scripts/probe.py --help` describes recorded-image probes and optional NF4 export.
Exported weights are stored under `models/navila-nf4` and verified against the
run's `export_manifest.json`. Re-run the probe with that model path to test reload.

Large models and disposable work copies are path-specifically ignored; source,
patches, provenance, input fixtures, logs and manifests remain visible to Git.

## Authors' inference hardware and communication

NaVILA paper v2 Appendix C4 reports a single RTX 4090 at roughly 1 FPS. Its AWQ
table also uses RTX 4090. Training GPU-node counts are not inference requirements.
[Paper](https://arxiv.org/html/2412.04453v2).

The public NaVILA-Bench implementation supplies a TCP socket client/server:
`scripts/navila_eval.py:157` samples eight frames, JPEG/base64 encodes them and
sends JSON `{images, query}` with an eight-byte big-endian length prefix;
`scripts/vlm_server.py:75` processes the request and sends back length-prefixed
JSON. CLI defaults are `localhost:54321`, allowing simulation and inference on
one host. This source establishes the simulation protocol, not the physical
network used in the paper's real-robot trials. The released benchmark server
accepts W16A16 only; its presence does not establish a published AWQ server.

- [Pinned client](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/scripts/navila_eval.py)
- [Pinned server](https://github.com/yang-zj1026/NaVILA-Bench/blob/e9d2db12ce5788c0f987d734c0094100b6bc0d3a/scripts/vlm_server.py)

The current deployment uses SSH for setup/artifact transfer and local calls
within the GPU host for recorded-image inference. It opens no public inference
port. A future colocated simulator would not stream each frame through the Mac.
