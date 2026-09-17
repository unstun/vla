# Archive Context

Archive requested explicitly by Dr Sun: important information must be retained
locally. Local date/time: 2026-09-16 21:32 America/Los_Angeles
(2026-09-17 04:32 UTC). Stage: experiment + analysis.

Project root and sole source of truth: /Users/sun/tongbu/study/phdproject/vla.
Memory root: /Users/sun/tongbu/study/phdproject/vla/bigmemory.

## Session summary

Dr Sun first selected MIP with DeepSeek Harness on gpu5070ti, authorized the
Matterport download, configured the key on the server and requested a real
trial. That earlier result remains in
.pipeline/experiments/2026-09-16_mip_5070ti/REAL_EPISODE_RESULT.md and the
pre-archive hot snapshot; no MIP run is performed during this archive.

The subsequent architecture decision was Pi plus Cortex/EMOS-compatible robot
tools to independently reimplement the supportable HarnessVLN mechanisms,
using Isaac Lab, Lite3 V12, native PCT/SCAN and eventually real localization.
Official paper-score reproduction and deployment readiness are separate claims.
Sibling machine-dog and machine-dog-nav repositories are read-only. The selected
bridge pin is 848b4aecd01237805e0564c88d3ba09146fd2353. Pi/Cortex real-service
integration, vision grounding, graph memory, SLAM and physical deployment remain
open; a fixture loop is not the deployed harness. User allowed GPT-5.5 medium
execution subagents with lead acceptance. Archive agents inherit the current
parent model according to the archive skill.

One continuous native PCT/SCAN/V12 Isaac pilot,
two_goal_20260916T162236Z_p2b_actual4, completed cancel/stop/resubmit and two
arrivals in 16.52 simulation seconds. Independent review passed 41 checks and
34/34 returned hashes. This is one known-map, simulator-truth spatial pilot,
not reliable repeated navigation or language/SLAM validation.

Dr Sun then asked to test live point clouds and requested more GPU use. An OFF,
software RViz and NVIDIA RViz+NVENC condition each ran 45 simulation seconds.
Actual NVIDIA renderer and hardware encoder were verified. GPU display used
approximately 2843 points per frame and showed 9-10 FPS. Physics wall time was
56.839/58.512/58.422 seconds; sampled active GPU memory peaks were
7082/7121/7445 MiB. GPU display+capture had +2.786% wall/sim time and +363 MiB
relative to OFF. No telemetry frames dropped. These are one exploratory pair,
include a protected stationary tail and do not establish dense-map/long-run
performance. Three new navigation trials all failed on A2 resubmission, including
OFF. GPU visualization success is separate from complete-navigation acceptance.
Returned hashes were 38/38,46/46,47/47. A separate run-specific-window startup
qualification passed with 10/10 hashes. A decoded 58-second local preview is
pointcloud_display/pointcloud_gpu.mp4. GPU rendering/NVENC is now the display
wrapper default; no physical actuation occurred.

Dr Sun requested investigation. The captured chain is: cancel reached
WAIT_TARGET, new route accepted into GEN_NEW_TRAJ, SCAN refined candidates
exceeded the unchanged acceleration gate, no second spline reached the
controller, initial_heartbeat_missing caused a protected fault stop. The later
generation-cancel rejection is a consequence, not the root cause.

Root and subagents built a true native C++ SCANPlannerManager::reboundReplan
repro using pinned scan_03 and actual Foxy libraries, an empty map and fresh
process per case. No Isaac, controller, cancellation or GPU workload was needed
to reproduce the same failure. Four derived start/goal cases were repeated
three times with seed zero. Original failed-resume failed 3/3; the other nine
calls passed. Native instrumentation showed true polynomial end T=1.73070084s,
last sample t=1.6s, sampled endpoint acceleration1.77813133m/s^2 versus true
endpoint approximately0. Refinement retains ~1.778376817m/s^2, above1.5.
Successful actual4 resume instead has T=1.70109638s and sampled1.47762351,
just below1.5; the stopping positions differ by about5cm.

The candidate changes only evaluateAcc(t) to evaluateAcc(time) in the isolated
manager copy. All4cases x3repeats pass (12/12), without changing limits or
deadlines. Failed-resume refined maximum acceleration drops to0.590244562.
Original/candidate each match67native source files,380installed files and
15diagnostic package files; both return16/16 artifact hashes. Independent
read-only review supports the mechanism. comparison.json passes9 checks.
Production materializer and scan_03 remain unchanged. No corrected Isaac
closed-loop trial has run. Candidate endpoint offset is approximately3.5cm;
endpoint/collision/random-init/later-replan/full-episode behavior remains to be
validated before production adoption. Attribute the defect only to the frozen
implementation used here, not unverified official upstream code.

## Primary evidence

All following paths are relative to the experiment root
.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/:

- README.md, RESULT.md, P2B_RESULT.md.
- p2b_execution/qualification/actual4_lead_review/result.json.
- pointcloud_display/RESULT.md, gpu_comparison.json, software_comparison.json,
  preview_provenance.json, visual_review.json, final_cleanup.json.
- scan_replan_diagnosis/RESULT.md, PLAN.md, comparison.json,
  independent_review.json, inputs/cases.json, inputs/planner.yaml.
- scan_replan_diagnosis/runs/native_original_20260916T180500Z/returned_artifacts/.
- scan_replan_diagnosis/runs/native_true_end_20260916T180700Z/returned_artifacts/.

Current Trellis task: .trellis/tasks/09-16-emos-harnessvln-reimplementation,
status in_progress. Keep it active. No remote execution, source fix, archive of
the overall task, or external push is authorized as an archival side effect.

Pre-existing hot files were snapshotted byte-for-byte at
bigmemory/冷区/改动记录/2026-09-16_2129_pre-harnessvln-hot-zone/.
Keep all unrelated InternVLA, MIP, camera and historical decisions discoverable
through that snapshot and existing source links. Do not silently close them.

## Archive triage

Q1 changes, Q2 nontrivial pitfall, Q4 decisions and Q5 a bounded diagnosis
milestone: yes. Q3/Q7/Q9 new external survey/literature: no new claims required.
Q8 experimental evidence: yes. Q10 new terminology: no. Preserve existing
literature edits. Root owns source/evidence manifests, CLI knowledge gate,
global memory extension, final validation and selective local Git backup.

## Source-verified details added after the first archive gate

The first gate reported insufficient summary detail, not a contradiction in the
underlying records. The following details were checked directly on 2026-09-17
04:39 UTC and are added for the gate's summary-only comparison:

- Frozen GPU observer/config.json records pointcloud_qos=BEST_EFFORT KEEP_LAST
  depth1, decay_seconds=0 and topic=/quad_0/cloud_raw.
- scan_replan_diagnosis/container_cases.py calls each actual C++ process with
  timeout=20. This is the recorded 20-second per-case wall limit.
- inputs/cases.json labels each fixture position as PCT-request ground pose
  plus the frozen nominal0.35m body-height offset, not exact SCAN argument capture.
- pointcloud_display/final_cleanup.json records all four ports free, no active
  containers, all registered owned PIDs absent and NVIDIA encoder sessions0 at
  the end of the prior display experiment. Card memory then was204MiB. This is
  historical cleanup evidence, not a new live-host check during archival.
- The earlier Pi-only offline slice RESULT.md records11Python and5Pi/transport
  checks on Mac andLinux plus11/11returnhashes; its two moves are scripted
  fixture calls. It is separate from real-service and language navigation.

The second gate identified two further omitted details, now verified directly:
- The software-RViz run's returned pointcloud_observer/session.json records an
  ffmpeg command using libx264. GPU rendering/capture instead uses h264_nvenc.
- analyze_native.py reads existing local native-run artifacts, checks hashes,
  compares outcomes and writes comparison.json. It imports no process/network
  launcher and does not launch any remote experiment.
