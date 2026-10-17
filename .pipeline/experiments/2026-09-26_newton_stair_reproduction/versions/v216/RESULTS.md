# v216: supported, interruptible PD transfer

14 behavioral tests passed on gpu5070ti. The pre-fix replay of this suite
against v208 produced 35 assertion failures, including unsupported admission
and failure to abort transfer. The candidate returns the live policy target and
base gains in the same control update for each disturbance, including the
2 s completion boundary and simultaneous new-command case.

Four-foot support >=10 N is required throughout the unchanged 0.25 s entry
dwell. Unequal support remains allowed. During transition, existing tilt,
linear/angular speed and >1 N contact thresholds are checked every control
update, with immediate RL return and the existing 0.5 s reentry lockout.
Fixed-stand disturbance persistence, motor limits, target cap and policy remain.

Integrated once in v217: the previous stair fall did not occur; unsupported
states stayed under RL, and a later supported transfer completed. That trial
still failed navigation, so this is not full-route qualification. See v217.
