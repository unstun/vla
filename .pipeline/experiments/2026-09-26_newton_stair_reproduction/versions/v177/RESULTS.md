# v177 original-route repetition results

All five serial Linux runs qualified on the unchanged original Building map and
original spatial start. All30replacement handoffs have measured-stop evidence;
no falls; every run passed finalXY/Z/yaw, PDhold and state-copyback checks.
Macv176 separately qualified one full route with6handoffs. Mac and Linux counts
are not pooled. The55compact Linux return files were individually SHA-verified.

The sole behavior change from Linuxv175 is the generated local spline finish
radius15cm→2cm. All649native source files match Macv176. Native controller,
planner, PCT and BT binaries remain the verified Linuxv175 underlay. The final
mission-goal tolerance is a separate unchanged contract.

| Attempt | Arrived | Sensor path (m) | Full physics (s) | Recovery handoffs | Longest low-speed pause (s) |
|---|---|---:|---:|---:|---:|
| 01 | yes | 76.846 | 162.584 | 12 | 10.694 |
| 02 | yes | 76.946 | 123.224 | 4 | 6.496 |
| 03 | yes | 77.097 | 143.007 | 8 | 6.596 |
| 04 | yes | 76.871 | 118.726 | 3 | 5.997 |
| 05 | yes | 76.910 | 122.444 | 3 | 6.596 |

The preceding v175 cohort passed2/5; its three failures and all raw records are
retained. The recorded failure05 controller fixture directly demonstrates old
zero output at4.9246cmendpoint error and candidate inward correction. A1cmpose
still stops. This confirms the deadband defect and the parameter's immediate
control effect. The two whole-route cohorts have different asynchronous timing;
they are not an exact paired-schedule causal experiment.

## Limits

The longest low-speed pause remains10.694s. Individual planning rounds reach
497.846ms; the largest per-run99thpercentile is315.425ms. This is therefore
original-scenario completion/recovery validation, not30Hz or smooth-navigation
acceptance. The known post-revocation physical-drift class was not separately
eliminated by this change; its old already-occupied stopped-pose replays still
fail closed. The five fresh complete runs did not reproduce an unrecoverable
stop. No Jetson, real-robot, other-map, or broad statistical reliability claim.

## Reproduction and retained evidence

Local source is this repository; run `run_cohort.py` from the frozen Linuxv177
execution copy after verifying `freeze_host.py verify` and resource admission.
The launcher fixes the original map, spatial start, CPUphysics, policy, per-run
identity, ports, source/install receipt and bounded execution. It runs five
serial trials and closes each before proceeding. Existing attempt directories
must be preserved; a new cohort needs distinct owned run identities.

Raw records remain in `/data/sun/vla_mppi_20261009/trials/v177_full_candidate_attempt01`
through`05`, with293files per trial and per-file SHA/symlink provenance returned
under `results/repeats/*/remote_artifacts.json`. Compact checks, exact source
manifest, native build receipt, inherited55colcon basis,18host tests,2profile
cases and recorded native control counterfactual are local. The initial host
precheck omitted the already-pinned vendored dependency path; its immediate
rerun also encountered the historical-port test's ownTIME_WAIT. Both logs are
retained and the clean final18-test run passed. Production ports were unchanged.

Displayv178 will show the first repetition in full, including all12handoffs and
long pauses. It replays recorded poses with no physics steps and is separate
from the five physical outcomes.
