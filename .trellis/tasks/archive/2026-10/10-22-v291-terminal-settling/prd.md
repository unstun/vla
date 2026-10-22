# v291 terminal ownership and zero-command settling

User authorization: 2026-10-22 implement the next convergence-plan steps, component and offline validation only. No subagents or new physics.

Parent: frozen v290 navigation plus frozen v216 stance. Accepted v232/v233 unchanged.

Requirements:
- TrackingNode alone decides terminal centering/yaw/braking. Controller consumes its result and retains measured completion/timeout checks.
- Use the existing 5 cm centering deadzone as inner braking entry, original 25 cm / 20 cm / 0.25 rad final acceptance and half-yaw entry band. Outside the deadzone use bounded proportional correction, avoiding asymptotically tiny pull commands.
- Keep collision emergency stops and cancellation dominant.
- During zero-command STAND_SETTLING, stabilize already loaded, quiet legs with torque-matched joint targets at unchanged RL gains, while unlanded legs keep their policy targets. This is a candidate stop controller, not a measured drift reduction.
- Keep all-foot >=10 N / 0.25 s dwell, speed/tilt gates, formal PD gains and transition checks. New command, unsafe body motion or contact loss releases settling assistance; truthful ownership and applied action history.
- Run native tests, captured controller/stance replays, inherited regressions, strict53 cases with independent existing audit. No physical attempts.
- Mark HTML unify/handoff/component only after their respective checks. Do not mark freeze (includes unselected new routes), paired experiments or adoption complete.
