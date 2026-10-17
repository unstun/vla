# v216: supported and interruptible PD transfer

Parent: frozen v208 locomotion. Navigation remains unchanged in this version.

Require each measured foot force >= existing ENTRY_FOOT_FORCE_N (10 N) for
all of the existing 0.25 s stillness dwell. Keep uneven but supported loads;
do not restore the rejected load-share balance gate. Insufficient support
keeps RL ownership. During STAND_TRANSITION, any existing body speed, angular
speed, tilt or contact-loss limit aborts immediately to RL with the existing
reentry lockout. FIXED_STAND retains its existing disturbance persistence.
No nominal pose reset, policy, motor, target cap or crossfade retuning.

Regression first against v208: each absent foot, partial support and dwell
reset; every disturbance at early/middle/final transition including completion
boundary; immediate applied policy target/gains, reentry lockout, valid uneven
support and final fixed stand. Build/test execution is gpu5070ti only.

Local source of truth is this version directory. Sync by SHA-256 manifest;
remote copies are execution-only. Return test outputs and source hashes before
claiming component validation. Full physics belongs to v217 and is not implied.
