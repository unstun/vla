# NaVILA 8B quantized inference on RTX 5070 Ti

Dr Sun selected NaVILA and authorized trying quantized deployment on 2026-09-08.
This continues the navigation model comparison, with bounded pretrained
inference and environment preparation authorized. No training or robot motion.

Acceptance: pin source and official checkpoint; preserve the existing simulator
environment; load actual four-bit language layers on the 5070 Ti; execute the
upstream image/history preprocessing and navigation prompt with Chinese and
English instructions; record raw actions, timing, GPU memory, input hashes,
runtime versions and failures; retain a reusable launcher and verified local
artifacts. Export/reload the quantized checkpoint if supported. This is an
open-loop deployment probe, not closed-loop navigation or metric-stop validation.

The official source includes NF4 loading; the paper reports AWQ W4A16. Use the
available NF4 entry point, disclose the distinction, and measure resources anew.

Local truth: `.pipeline/experiments/2026-09-08_navila_8b_quantized_5070ti`.
Execution copy: `/home/sun/vla_exec/2026-09-08_navila_8b_quantized_5070ti`.
Sync gate: source/input SHA-256 equality before inference; evidence and exported
quantized files verified after return. Limit each inference invocation to 600 s.
