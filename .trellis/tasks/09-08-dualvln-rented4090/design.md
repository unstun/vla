# Design

Local truth: `/Users/sun/tongbu/study/phdproject/vla`. Task files: `.pipeline/experiments/2026-09-08_dualvln_rented4090`. Remote execution copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090` on `ubuntu@117.50.179.202`.

Pin InternNav `7a5c62400ac45b313d9b709c740b64191556a242` and checkpoint `a698a9e898b4001621a319e1bc89f02ec715cc86`. Keep pristine source separate from the task work copy; record each compatibility change. Start with Python 3.10, Torch 2.6/cu124, Transformers 4.51 and real FlashAttention2. Use the original realworld agent on released RGB fixtures; its notebook uses dummy depth/pose, so that phase is open-loop only.

For simulation prefer a small existing public scene and original agent output consumer; retain input RGB/depth, actual camera transforms, raw discrete actions/trajectories and applied movement. Define the chosen simulator/controller contract before its run. Model and simulator may run in separate processes/hosts if GPU memory requires it. Preserve the existing Isaac Sim 5.1 container.

Each inference run has a 600-second deadline; the initial closed-loop case has at most 1800 seconds and 200 model-driven steps. Own process groups only. Public unmodified checkpoint bytes are an execution cache, reconstructible from immutable upstream revision and verified hashes; code, input fixtures, patches and run evidence return locally. No unique trained/exported model is produced.
