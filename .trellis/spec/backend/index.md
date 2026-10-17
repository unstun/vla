# Backend Development Guidelines

> Pre-baseline backend guidance for the VLA project.

---

## Overview

No backend implementation has been imported. Only the pre-baseline quality and
evidence contract is active; the other files remain scaffolds until real code
establishes conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Deferred: no imported backend |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | Deferred: no database selected |
| [Error Handling](./error-handling.md) | Error types and propagation | Deferred: no runtime selected |
| [Quality Guidelines](./quality-guidelines.md) | Baseline, interface, and evidence gates | Active |
| [Simulator Inference Evidence](./simulator-inference-evidence.md) | Bounded upstream trials, clocks, resources, and artifact integrity | Active for upstream experiments |
| [Newton Reference Progress](./newton-reference-progress.md) | Shared map-resolution progress rule and native short-window regression | Scoped to the v6 Building integration |
| [Newton Minimum Cruise](./newton-minimum-cruise.md) | Planned speed floor, boundary ramps, native retiming and measured-speed distinction | Scoped to the v7 local integration |
| [Newton Sensor Port Evidence](./newton-sensor-port.md) | Original-link exclusion, preserved occlusion and current skin controls | Scoped to the 2026-09-26 local experiment |
| [Newton Clock Bridge](./newton-clock-bridge.md) | Cross-OS clock mapping, original applied-state validation and byte-exact return | Scoped to the 2026-09-26 local experiment |
| [Newton Replay Rendering](./newton-replay-rendering.md) | Authored material, linear color, visibility and immutable-state video | Scoped to the 2026-09-26 local experiment |
| [Newton Artifact Retention](./newton-artifact-retention.md) | Streaming MP4, bounded post-run retention, verified archives and restoration | Default for new Newton recording/rendering work |
| [Newton Linux Execution](./newton-linux-execution.md) | gpu5070ti host port, same-host comparison and output ownership | v123/v124 execution scope |
| [Newton Contact Capacity](./newton-contact-capacity.md) | Native capacity estimation, speculative-contact scoring and geometry-only input gates | Scoped to the 2026-09-26 local experiment |
| [Newton PD Startup](./newton-pd-startup.md) | Pinned SDK crouch/stand control, measured policy handoff and navigation gating | Scoped to the 2026-09-27 flat startup trial |
| [Newton PD Hold](./newton-stance-hold.md) | Existing PD/RL state machine, measured foot support and long-route execution | Scoped to the 2026-09-27 empty-floor trial |
| [Newton Support Coverage](./newton-support-coverage.md) | Static subcell floor-gap veto and captured torso/optical-frame separation | Scoped to v134 simulator map correction |
| [Shared Floor and Environmental Costs](./newton-shared-environment.md) | Diagnostic floor association, unchanged hard admission, shared soft-score contracts and attribution | Scoped to v223/v224 component and replay work |
| [Native Callback and Process Failures](./newton-callback-failure.md) | Optimizer cancellation, finite soft heading, callback containment and run-bound FAILED closure | v232 offline repair scope |
| [Newton Versioning](./newton-versioning.md) | User-designated v3 baseline, immutable source snapshots and version-bound trials | Active for local Newton integration |
| [Newton Stair Repairs](./newton-stair-repair-contracts.md) | Ground/support, seed ownership, stop replies, endpoint evidence and trajectory epoch | Scoped to Newton v8–v59 |
| [Newton Asynchronous Mapping](./newton-async-mapping.md) | Compact polls, immutable map revisions, publication leases and guarded duplicate backlog reduction | Scoped to Newton v79–v82 |
| [Native Trajectory Validation](./newton-trajectory-validation.md) | Independent native PVA/dynamic/collision/epoch checks and caller-owned leases | Scoped to v127 MPPI adaptation 3 |
| [Foxy SCAN Plugins](./nav2-foxy-scan-plugin.md) | PCT/SCAN plugins, BT mission gateway, shared 3D map projection, stop proof and source export | Scoped to Foxy v86+ integration |
| [Quantized Inference Evidence](./quantized-inference-evidence.md) | Low-bit state, resource measurements, export/reload, and action claim boundaries | Active for quantized VLA probes |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging and run identity | Deferred: no runtime selected |

---

## Activation Gate

After a clean baseline is imported, inspect real code before activating a
guideline. Document actual paths, commands, tests, and anti-patterns; do not
copy conventions from `machine-dog-nav` merely because it is the candidate
source.

---

**Language**: All documentation should be written in **English**.
