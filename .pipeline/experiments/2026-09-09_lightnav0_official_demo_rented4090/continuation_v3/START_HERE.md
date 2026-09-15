# Manual Opus handoff

Status: **prepared_not_dispatched**. This package prepares the next three
official LightNav-0 runs on rented4090 with complete video and state evidence.
The lead has not started those runs or dispatched Opus.

Paste this into the Opus session that has access to the local VLA repository:

```text
Continue the LightNav-0 official-case reproduction on rented4090. Read and execute the complete package at /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/EXECUTION_PACKAGE.md, including its VISUAL_SPEC.md and RESEARCH.md. Preserve the official vLLM BF16 configuration and all old evidence. Complete the three bounded fixed-case runs, return the real multi-view MP4s and traceable outcome analysis locally, and write continuation_v3/OPUS_RETURN.md. Preserve failed runs and report navigation failure honestly. Do not stage or commit.
```

Read in order:

1. [Execution package](EXECUTION_PACKAGE.md): scope, ownership, commands, budgets and return.
2. [Visual specification](VISUAL_SPEC.md): four-panel film, exact joins, camera/state replay and QA.
3. [Investigation](RESEARCH.md): verified defects, current host, primary sources and uncertainty.

Static preview: [orthographic scene view](research/static_probe_02/topdown_static.png).
It is a real renderer feasibility check at the original spawn, with no VLA call
and no simulator step; it is not a new navigation result.

Reuse the existing verified model/demo environments and full checkpoint. The
main work is reliable capture, offline visualization and measured arrival/STOP
analysis. A good video is required even when the official navigation task fails.
