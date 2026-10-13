# v164: bounded checked steering toward side/back directions

Stage: experiment and analysis. Native/hostparentv163. On its actual27m
stopped-stair failure, measured bodyyaw1.383561rad is collisionfree at rest.
Every forward5cm segment near that heading is blocked.33of65sampled5cm
directions pass the unchanged native segment check, including side/back paths.
The actual parent FSM fails all6reference prefixes and has no forward steering
proposal; this is reproduced using545retained scans and originalmap inputs.

Keep the original5near-forward offsets first; add +/-22.5,+/-45,+/-90,180deg.
Check the full in-place angular sweep at no coarser than original1.40625deg
steps, at measured and immutable startpositions. Preserve fullsegment/endpoint
checks, one accepted5cm prefix per owner, freshmap/body, stoppedonly andno false
referenceprogress. Retain maximum5expensive full-manager attempts. Normal
reference planning is unchanged. No reverse-body command mode orrelaxedmask.

Require actual captured-corner FSM regression for the new stoppedstairs AND
the priorv156fixture, fullPVA/dynamics/collision and originalguards. Controller
uses the normal checked turn-and-track path. Freeze then original-start local
physics; componentpass is not physicalrecovery acceptance.
