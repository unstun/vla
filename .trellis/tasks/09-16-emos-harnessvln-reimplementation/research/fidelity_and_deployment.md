---
origin: ai_only
reviewed: false
---

# HarnessVLN Fidelity And Physical Deployment Matrix

Source: locally captured HarnessVLN 2609.15195v1 HTML and PDF, especially
Sections 3.1-3.2 and Appendix configuration/tool descriptions. The official
repository was rechecked on 2026-09-16 and still contains only a README.
Full prompt and implementation fidelity cannot yet be independently established.

| Mechanism | Required implementation | Evidence needed before completion |
|---|---|---|
| Task state | Stable subgoal IDs; pending/active/completed/blocked; evidence-backed transitions | Different instructions cause different observable subgoals; no completion from model prose alone |
| Event memory | Working, progress and reflection memory; reflection owns complete event traces and graph annotations retain references | Event replay reconstructs state; context omits stale/irrelevant data without losing task evidence |
| ST Graph | Places, entities, observations, spatial/navigability relations and applicable failure records | Revisit/loop/localization-change cases preserve or invalidate the correct evidence |
| Retrieval | Local IDF-weighted cosine relevance, recency/salience and bounded task-conditioned failure penalty | Deterministic ranking cases plus a task that requires recalling a visited location |
| Grounding | Active target to view and image region, with real perception/model output | Stored raw image, region/mask, confidence and association with the actual intended entity |
| Depth projection | Valid aligned depth and capture-time camera pose | Known-geometry reprojection error and invalid/uncertain depth tests |
| Proposal validation | Tool schema, evidence freshness, geometry, reachability and subgoal consistency | Contradictory, stale, unreachable and forged requests rejected before motion |
| Navigation executor | Persistent PCT/SCAN/V12 action service with real feedback | Sequential goals, path acceptance, cancellation, measured motion, no state reset |
| Recovery/backtrack | Applicable failure history and verified return to a visited place | Blocked route, changed scene and unsuccessful revisit recover or fail explicitly |
| Task stopping | Semantic AND geometric AND task-progress evidence | Near wrong object, near goal too early, uncertain depth and stale observation do not end successfully |
| Independent evaluation | Hidden scoring goal/labels; actual native terminal reason | Leakage audit and all outcomes preserved, including model false-arrival claims |

## Published constants to retain or explicitly vary

The paper reports place/entity merge radii 0.75/1.0 m, top-3 retrieval seeds,
one-hop expansion, maximum 5 returned places, recency/salience weights 0.3/0.3,
and a 0.5 applicable-failure penalty capped at 1.0. These are initial
paper-reference values, not validated real-Lite3 tuning results.

Geometric stop evidence uses fresh median depth from a 5x5 anchor patch, maximum
patch standard deviation 0.5 m, and a 2.5 m depth threshold; unreliable depth
uses projected-target proximity with a 1.0 m threshold. Semantic and progress
checks still apply. These are not benchmark goal-distance thresholds and do
not specify braking distance or collision clearance.

The paper's 0.25 m/30-degree actions, 0.88 m camera, 0.10 m agent radius,
FMM/NavDP executor and R2R/RxR/ObjectNav evaluation are a different embodiment
and protocol from continuous PCT/SCAN/V12 in Isaac Lab. Keep them in a separate
paper-reference profile. Do not use the paper's small body radius for Lite3
collision geometry or silently claim matching benchmark scores.

## Grounded implementation substitutions

- Pi agent-core is the model/tool loop; it is not the spatial graph.
- Cortex supports tool/component integration; its planner is not nested inside
  Pi and its default parameter/raw-action tools are not exposed to the model.
- EMOS Memory/eMEM is a possible storage provider, not an automatic equivalent
  of the paper's hierarchical memory and retrieval equations.
- PCT/SCAN replaces the paper's navigation executor. Keep this substitution
  constant when evaluating changes to the upper harness.
- DeepSeek can reuse the previously selected provider, but is a model
  substitution. Paper-model results require their own declared configuration.
- Reconstructed prompts are versioned artifacts and labelled reconstructed;
  short prompt excerpts cannot establish exact author-prompt reproduction.

## Deployment-specific tests

The physical acceptance profile uses sensor-derived localization and calibrated
RGB-D. Ground-truth simulator pose is confined to the labelled diagnostic mode
or evaluator. Distinguish prebuilt geometric map, online mapping and semantic
memory; possessing a map is not evidence that SLAM is running.

Use the same goal/feedback/cancel contract in simulation, recorded real sensors
and receive-only live operation. Test localization failure/map changes,
sensor delay, unavailable targets, failed planning, collision/contact signals,
transport disconnect, duplicate requests and model API failure.

Model task stop is different from emergency/operator stop. The latter has
independent command authority and never waits for semantic completion. Verify
the existing V12 watchdog and the actual contact policy rather than describing
all non-foot contacts as automatic stops.

Real motion is a separately authorized, supervised stage. Deployment readiness
is bounded to a frozen platform/rig/localization/control/scene envelope and
requires repeat runs; one successful video or a CPU test suite is insufficient.
