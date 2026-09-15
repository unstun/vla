# DualVLN BF16 inference and bounded simulation

Dr Sun selected InternVLA-N1 DualVLN, provided the rented RTX 4090 server, and authorized trying original-precision inference followed by one simulator scene and a local video on 2026-09-08. This permits isolated dependency/model installation and bounded pretrained inference/simulation. No training, robot actuation, modification of existing locomotion work, or stopping unrelated processes.

Acceptance: pinned upstream/checkpoint; actual BF16 CUDA model outputs and measured memory/latency; one bounded simulated observation-action loop with actual pose change and a decoded, visually inspected video; local raw outputs, configs, compatibility patches, manifests, and a candid report. Model inference alone is a partial result. A new small-scene adapter is a functional simulator trial, not reproduction of full paper metrics. Chinese instruction and learned-stop behavior remain separate measurements.

## Approved direction on 2026-09-09

Dr Sun selected a small evaluation through the official repository protocol and
requested a new English Opus prompt. The next package is
`.pipeline/experiments/2026-09-08_dualvln_rented4090/OPUS_OFFICIAL_REPRODUCTION_PACKAGE.md`.
Use the pinned official Habitat evaluator, original BF16 checkpoint, and three
fixed R2R `val_unseen` episodes from one Matterport3D scene. Preserve original
instructions, starts, goals, sensors, and control behavior; save videos and raw
results for successes and failures. This is a bounded protocol reproduction
check, not a claim to reproduce full paper metrics. The old custom-scene results
and open corrections remain preserved. Preparing this package does not dispatch
Opus or establish that official dataset access and the evaluator environment are
ready.

## Public-scene direction on 2026-09-09

Following the MP3D access blocker, Dr Sun pointed to the available castle and
Van Gogh room assets. The next prepared package is
`.pipeline/experiments/2026-09-08_dualvln_rented4090/OPUS_PUBLIC_SCENES_PACKAGE.md`:
retain the official model and evaluator, adapt scene/task data, freeze two short
cases before inference, and return real first-person/top-down videos including
failures. This is custom public-scene functional evaluation; it does not replace
or complete the still-unexecuted R2R benchmark subset. Package preparation is not
dispatch or runtime evidence.
