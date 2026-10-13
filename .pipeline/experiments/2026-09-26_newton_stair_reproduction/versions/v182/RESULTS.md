# v182: stopping after higher walking commands

Stage: experiment + analysis. Status: executed and measured in the local Mac
Newton runtime. This is a diagnostic result, not a locomotion repair, navigation
qualification, Linux repeat, original-training reproduction or hardware result.

## Correction and result

The preceding v179 commands (0.2, 0.35 and 0.5 m/s) were all below the project's
existing 0.6 m/s planned-cruise operating rule. They remain useful low-speed
controls, but did not justify the earlier general diagnosis that the model
cannot stop in its intended operating range. The proposed standing takeover and
training remedies were premature and are not selected implementations.

Twelve v182 trials use 0.6, 0.8 and 1.0 m/s commands, with two first-walk durations
per speed on each terrain. Only command amplitude changes from the corresponding
v179 trial. All twelve schedules completed, including both full 10-second zero
commands and the intervening 3-second restart. There were no base-up fall aborts.
These are varied-duration conditions, not twelve independent training seeds.

| Terrain and cohort | Complete stop windows | Late excursion over 5 cm | Largest late excursion | Largest command-to-end displacement |
| --- | ---: | ---: | ---: | ---: |
| Flat, v179 low speeds | 12 | 4 | 31.15 cm | 60.81 cm |
| Flat, v182 higher speeds | 12 | 0 | 3.67 cm | 15.47 cm |
| Stair scene, v179 low speeds | 12 | 7 | 14.54 cm | 31.92 cm |
| Stair scene, v182 higher speeds | 12 | 4 | 10.08 cm | 20.63 cm |

"Late" excludes the first 2 seconds after the zero command and measures maximum
horizontal excursion from the first subsequent sample, through the remainder
of the 10-second window. Command-to-end displacement includes braking. The
5 cm threshold is a descriptive flag, not an upstream or accepted project
qualification criterion. Zero flagged stops is not proof of perfect stillness.

Flat-ground behavior improves substantially in this cohort. This supports
treating approach speed as an important condition for the tested policy/runtime;
it does not establish an exact universal minimum or prove that speed explains
every stop failure. In the stair scene, different speeds reach different contact
locations, so speed and stopping geometry are confounded. Some stops occur on
the approach or landing, rather than with every foot on a stair.

## Commanded and measured speed are different

Mean measured horizontal speed after the first second of each flat-ground walk
is 0.565–0.568 m/s for the 0.6 command, 0.779–0.780 for 0.8, and 0.988–0.991 for
1.0. Therefore the 0.6 command does not prove a measured 0.6 m/s minimum.
Across stair-scene walks the corresponding ranges are 0.565–0.586, 0.575–0.784,
and 0.902–0.958 m/s. The 0.8 command has one slower stair restart.

`results/speed_comparison.json` preserves every paired stop, actual walking
speeds and source hashes. `results/compare_speeds.py` is the executed analysis.
Position finite differences independently agree with mean state-speed values to
within 0.00345 m/s across these windows; this is a numerical cross-check, not an
external speed measurement.

## Minimum-speed source audit

The project rule in `.trellis/spec/backend/newton-minimum-cruise.md` is a planned
cruise requirement; it excludes braking, acceleration, turning and stationary
holds. It must not be implemented as a downstream clamp on every nonzero command.

The checkpoint-bound V12 training code also has an explicit dynamic low-speed
exclusion, based on remaining commanded distance and remaining episode time.
The archived configuration implies an initial ordinary per-axis bound near
0.200 m/s; special command branches can overwrite these samples. This is not a
fixed 0.6 m/s training minimum. The actual training command histogram remains
unavailable. See `results/minimum_speed_source_audit.json` and the v179 archived
training configuration. Do not merge these distinct meanings of "minimum".

The inspected upstream robot_lab command generator zeros horizontal commands
whose norm is at most 0.2 m/s; its base configuration actually selects that
generator. Its standing samples and reward terms are separate mechanisms.
This confirms that low-speed handling exists upstream, not that its threshold
can be copied to Lite3 or that its policy would pass these tests. Source:
[commands.py at 500399e](https://github.com/fan-ziqi/robot_lab/blob/500399ed75f510aeaff28705a8ce736c514dbec3/source/robot_lab/robot_lab/tasks/manager_based/locomotion/velocity/mdp/commands.py#L43-L47).

## Provenance and claim boundary

All stop samples verify zero effective command, policy joint ownership and
unchanged 20/0.5 gains. The current policy, observation mapping, contacts, factory
startup and original REJOIN remain unchanged. Each trial has one continuous
physical state. The inherited core is v177; the experimental parent is v179.
`parent_binding.json` clarifies the ambiguous inherited-parent field in the
already frozen manifest, without overwriting it.

All twelve raw archives and all thirteen members per archive were verified on
`gpu5070ti:/data/sun/vla_mppi_20261009/policy_stop_v182_mac/archives/`.
Returned receipts are under `results/raw_receipts/`. v183 renders these exact
recorded states with no additional physics, including all stop intervals.

No automatic stand takeover, policy, gain, training, navigation or hardware
change is approved by these results. The original v177 full-route stopped-pose
failure remains open; it used a different hold path. The diagnostic task does
not establish a repair of that failure.
