---
origin: ai_only
reviewed: false
---

# Selected Pi / Cortex Source Bindings

These are unmodified, pinned reference acquisitions, not upstream experiment
reproductions. `acquisition.json` records commit/tree identities; each
`*_sha256.json` records the local file hashes. Recreate with
`python3 references/upstream/2026-09-16_pi_cortex_harnessvln/acquire.py`.
Existing mismatched or dirty snapshots are rejected rather than reset.

## Pi

Release `@earendil-works/pi-agent-core@0.85.1` declares npm gitHead
`d981de1229ef899957bbe968bc8dcda02a21f477`. MIT license is in `source/pi/LICENSE`.
The package's `dist.integrity` is recorded in the manifest; installed package
and transitive dependency integrity/version bindings are frozen in the
experiment's `pi/package-lock.json`. Dependencies use Node >=22.19.0.

Original usage is the Quick Start in `source/pi/packages/agent/README.md`:
install `@earendil-works/pi-agent-core`, construct `Agent` with a model and
`streamFn`, and call `agent.prompt(...)`. That example uses a real model.
Our probe instead injects a deterministic provider into the real Pi runtime.

Relevant installed seams are `Agent`, `transformContext`, `beforeToolCall`,
`shouldStopAfterTurn`, `toolExecution: sequential`, and awaited `subscribe`
callbacks. These were checked in the actual release's `dist/agent.d.ts` and
`dist/types.d.ts`; current-main documentation alone is insufficient.

## Cortex / EMOS

EMOS `31b82958e7a1646b9af606184518333c97290f58` pins EmbodiedAgents
`c37ab75db4aba88bcc99d17f6eabac146ad46d20`. Both root LICENSE files are MIT.
The acquired EMOS snapshot has uninitialized gitlinks. Sugarcoat/Kompass and
other dependencies have not been fully acquired or built in this slice.

Upstream installation alternatives, from `source/emos/README.md` and
`docs/getting-started/installation.md`, include `emos install --mode container`,
`emos install --mode native`, and `emos install --mode pixi`. These installers
can resolve moving dependencies; a future execution copy must freeze actual
versions instead of treating those commands as a reproducible lock.
The pixi workspace targets Linux and ROS 2 Jazzy. `pixi run setup` additionally
builds the Kompass stack and registers user-level EMOS configuration. It has
not been run. No upstream curl-to-shell or system installation was executed.

Original robot demo: the recipe in
`source/emos/docs/recipes/planning-and-manipulation/cortex-navigation.md`.
It creates Planner/Controller/LocalMapper/DriveManager, perception, Memory,
Cortex and a Launcher. It requires ROS, sensor topics, a model endpoint and
robot configuration; it is not an inert import smoke.

Code seam map in `source/embodied-agents/agents/components/cortex.py`:

| Symbol | Existing behavior | Composition requirement |
|---|---|---|
| `_plan_task` / `_confirm_step` | Own model planning and confirmation policy | Do not invoke inside Pi's loop. |
| `_register_system_tools` | Discovers actions and exports parameter mutation | Filter at catalog and actual dispatch. |
| `_register_component_methods_as_tools` | Produces OpenAI-style function schemas | Potential schema reuse; no standalone public server. |
| `_execute_action_step` | Dispatches internal or registered system actions | Private ROS/lifecycle coupling needs a real integration test. |
| `_active_action_clients` | Tracks asynchronous robot goals | Preserve cancellation/feedback and uncertain-result handling. |

The offline gateway uses this shared function-schema format but does not import
Cortex. No assertion about Cortex runtime integration follows from that probe.

## HarnessVLN boundary

The paper repository is a README-only placeholder. Its task state, event/ST
Graph memory, grounding, validation and stopping mechanisms must be independently
implemented and compared under declared prompts/models/protocol. Pi is only
the loop runtime. A Kompass planner is not paper-equivalent FMM, and EMOS memory
retrieval is not automatically the paper's retrieval formula.
