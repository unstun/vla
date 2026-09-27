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
